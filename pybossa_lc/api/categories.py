# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import json
import time
import uuid
from flask import Blueprint, flash, request, abort, current_app, url_for
from flask.ext.login import login_required, current_user
from pybossa.util import handle_content_type, get_avatar_url
from pybossa.util import redirect_content_type
from pybossa.core import project_repo
from pybossa.core import uploader, importer
from pybossa.auth import ensure_authorized_to
from pybossa.forms.forms import AvatarUploadForm, GenericBulkTaskImportForm

from ..utils import *
from ..forms import VolumeForm, ExportForm
from ..exporters.csv_volume_exporter import CsvVolumeExporter
from ..exporters.json_volume_exporter import JsonVolumeExporter


BLUEPRINT = Blueprint('lc_categories', __name__)


def _get_export_form(method, form_data=None):
    """Return the custom export format form."""
    if not form_data:
        form_data = {}
    form = ExportForm(**form_data)

    if method == 'POST':
        for field in form_data.get('fields', []):
            form.fields.append_entry(field)
    return form


@login_required
@BLUEPRINT.route('/<short_name>/volumes')
def get_volumes(short_name):
    """Return all volumes enhanced with project data."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('read', category)
    category_vols = get_enhanced_volumes(category)
    unknown_projects = get_projects_with_unknown_volumes(category)

    response = dict(volumes=category_vols,
                    unknown_projects=unknown_projects,
                    category=category)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<short_name>/volumes/new', methods=['GET', 'POST'])
def new_volume(short_name):
    """Add a new volume."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    volumes = category.info.get('volumes', [])

    form = VolumeForm(request.body)
    form.category_id.data = category.id
    all_importers = importer.get_all_importer_names()
    form.importer.choices = [(name, name) for name in all_importers]

    new_volume = None
    if request.method == 'POST' and form.validate():
        volume_id = str(uuid.uuid4())
        new_volume = dict(id=volume_id,
                          name=form.name.data,
                          short_name=form.short_name.data,
                          importer=form.importer.data)
        volumes.append(new_volume)
        category.info['volumes'] = volumes
        project_repo.update_category(category)
        flash("Volume added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(form=form, new_volume=new_volume,
                    all_importers=all_importers)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<short_name>/volumes/<volume_id>/update',
                 methods=['GET', 'POST'])
def update_volume(short_name, volume_id):
    """Update a volume."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    volumes = category.info.get('volumes', [])

    try:
        volume = [v for v in volumes if v['id'] == volume_id][0]
    except IndexError:
        abort(404)

    form = VolumeForm(**volume)
    form.category_id.data = category.id
    all_importers = importer.get_all_importer_names()
    form.importer.choices = [(name, name) for name in all_importers]

    upload_form = AvatarUploadForm()
    import_form = GenericBulkTaskImportForm()(volume['importer'])

    def update():
        """Helper function to update the current volume."""
        try:
            idx = [i for i, _vol in enumerate(volumes)
                   if _vol['id'] == volume_id][0]
        except IndexError:  # pragma: no cover
            abort(404)
        volumes[idx] = volume
        category.info['volumes'] = volumes
        project_repo.update_category(category)

    if request.method == 'POST':
        # Process task import form
        if request.form.get('btn') == 'Import':
            import_form = GenericBulkTaskImportForm()(volume['importer'],
                                                      request.body)
            if import_form.validate():
                volume['data'] = import_form.get_import_data()
                update()
                flash('Volume updated', 'success')

        # Process volume details form
        elif request.form.get('btn') != 'Upload':
            form = VolumeForm(request.body)
            all_importers = importer.get_all_importer_names()
            form.importer.choices = [(name, name) for name in all_importers]

            if form.validate():
                volume['name'] = form.name.data
                volume['short_name'] = form.short_name.data
                volume['importer'] = form.importer.data
                update()
                flash('Volume updated', 'success')
            else:
                flash('Please correct the errors', 'error')

        # Process thumbnail upload form
        else:
            if upload_form.validate_on_submit():
                _file = request.files['avatar']
                coordinates = (upload_form.x1.data, upload_form.y1. data,
                               upload_form.x2.data, upload_form.y2.data)
                suffix = time.time()
                _file.filename = "volume_{0}_{1}.png".format(volume['id'],
                                                             suffix)
                container = "category_{}".format(category.id)
                uploader.upload_file(_file,
                                     container=container,
                                     coordinates=coordinates)

                # Delete previous thumbnail from storage
                if volume.get('thumbnail'):
                    uploader.delete_file(volume['thumbnail'], container)
                volume['thumbnail'] = _file.filename
                volume['container'] = container
                upload_method = current_app.config.get('UPLOAD_METHOD')
                thumbnail_url = get_avatar_url(upload_method, _file.filename,
                                               container)
                volume['thumbnail_url'] = thumbnail_url
                update()
                project_repo.save_category(category)
                flash('Thumbnail updated', 'success')
                url = url_for('.get_volumes', short_name=category.short_name)
                return redirect_content_type(url)
            else:
                flash('You must provide a file', 'error')

    response = dict(form=form, all_importers=all_importers,
                    upload_form=upload_form, import_form=import_form,
                    category=category, volume=volume)
    return handle_content_type(response)


@BLUEPRINT.route('/<short_name>/volumes/<volume_id>/export')
def export_volume_data(short_name, volume_id):
    """Export custom volume level data."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    volumes = category.info.get('volumes', [])
    try:
        volume_dict = [v for v in volumes if v['id'] == volume_id][0]
    except IndexError:
        abort(404)
    volume_dict['category_id'] = category.id
    volume = get_volume_object(volume_dict)

    motivation = request.args.get('type')
    fmt = request.args.get('format')
    if not (fmt and motivation):
        abort(404)

    if fmt not in ['csv', 'json']:
        abort(415)

    def respond_json(motivation):
        json_volume_exporter = JsonVolumeExporter()
        res = json_volume_exporter.response_zip(volume, motivation)
        return res

    def respond_csv(motivation):
        csv_volume_exporter = CsvVolumeExporter()
        res = csv_volume_exporter.response_zip(volume, motivation)
        return res

    return {"json": respond_json, "csv": respond_csv}[fmt](motivation)


@login_required
@BLUEPRINT.route('/<short_name>/exports', methods=['GET', 'POST'])
def exports(short_name):
    """Setup volume level data exports."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    export_fmts = category.info.get('export_formats', [])
    form_data = json.loads(request.data) if request.data else {}
    form = _get_export_form(request.method, form_data)

    if request.method == 'POST' and form.validate():
        export_fmt_id = str(uuid.uuid4())
        new_export_fmt = dict(id=export_fmt_id,
                              name=form.name.data,
                              reference_header=form.reference_header.data,
                              fields=form.fields.data)
        export_fmts.append(new_export_fmt)
        category.info['export_formats'] = export_fmts
        project_repo.update_category(category)
        flash("Export Format added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(export_formats=export_fmts, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<short_name>/exports/<export_id>', methods=['GET', 'POST'])
def update_export(short_name, export_id):
    """Update a volume level data export."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    export_fmts = category.info.get('export_formats', [])
    try:
        export_fmt = [fmt for fmt in export_fmts if fmt['id'] == export_id][0]
    except IndexError:
        abort(404)

    form = _get_export_form(request.method, export_fmt)

    if request.method == 'POST':
        form_data = json.loads(request.data) if request.data else {}
        form = _get_export_form(request.method, form_data)
        if form.validate():
            export_fmt['name'] = form.name.data
            export_fmt['reference_header'] = form.reference_header.data
            export_fmt['fields'] = form.fields.data

            try:
                idx = [i for i, fmt in enumerate(export_fmts)
                       if fmt['id'] == export_id][0]
            except IndexError:  # pragma: no cover
                abort(404)
            export_fmts[idx] = export_fmt
            category.info['export_formats'] = export_fmts
            project_repo.update_category(category)
            flash('Export format updated', 'success')
        else:
            flash('Please correct the errors', 'error')

    response = dict(export_formats=export_fmts, form=form)
    return handle_content_type(response)
