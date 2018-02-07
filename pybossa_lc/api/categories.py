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
from pybossa.core import uploader
from pybossa.auth import ensure_authorized_to
from pybossa.forms.forms import AvatarUploadForm

from ..cache import templates as templates_cache
from ..utils import get_enhanced_volumes, get_projects_with_unknown_volumes
from ..forms import *
from .. import json_volume_exporter, csv_volume_exporter

BLUEPRINT = Blueprint('categories', __name__)


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
    """List or add volumes."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    volumes = category.info.get('volumes', [])

    form = VolumeForm(request.body)
    form.category_id.data = category.id

    if request.method == 'POST' and form.validate():
        volume_id = str(uuid.uuid4())
        new_vol = dict(id=volume_id,
                       source=form.source.data,
                       name=form.name.data,
                       short_name=form.short_name.data,
                       media_url=None)
        volumes.append(new_vol)
        category.info['volumes'] = volumes
        project_repo.update_category(category)
        flash("Volume added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(form=form, volumes=volumes, category=category)
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
    upload_form = AvatarUploadForm()

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
        if request.form.get('btn') != 'Upload':
            form = VolumeForm(request.body)
            if form.validate():
                volume['name'] = form.name.data
                volume['short_name'] = form.short_name.data
                volume['source'] = form.source.data
                update()
                flash('Volume updated', 'success')
            else:
                flash('Please correct the errors', 'error')
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

    response = dict(form=form, upload_form=upload_form, category=category)
    return handle_content_type(response)


@BLUEPRINT.route('/<short_name>/volumes/<volume_id>/export')
def export_volume_data(short_name, volume_id):
    """Export custom volume level data."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    export_fmts = category.info.get('export_formats', [])
    export_fmt_ids = [fmt['id'] for fmt in export_fmts]
    volumes = category.info.get('volumes', [])

    try:
        volume = [v for v in volumes if v['id'] == volume_id][0]
    except IndexError:
        abort(404)

    ty = request.args.get('type')
    fmt = request.args.get('format')
    if not (fmt and ty):
        abort(404)

    if fmt not in export_fmts:
        abort(415)

    def respond_json(ty):
        if ty not in export_fmt_ids:
            return abort(404)
        res = json_volume_exporter.response_zip(volume, ty)
        return res

    def respond_csv(ty):
        if ty not in export_fmt_ids:
            return abort(404)
        res = csv_volume_exporter.response_zip(volume, ty)
        return res

    return {"json": respond_json, "csv": respond_csv}[fmt](ty)


@login_required
@BLUEPRINT.route('/<short_name>/exports', methods=['GET', 'POST'])
def exports(short_name):
    """Setup volume level data exports."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    templates = templates_cache.get_by_category_id(category.id)
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

    response = dict(export_formats=export_fmts, templates=templates, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<short_name>/exports/<export_id>', methods=['GET', 'POST'])
def update_export(short_name, export_id):
    """Update a volume level data export."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    templates = templates_cache.get_by_category_id(category.id)
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

    response = dict(export_formats=export_fmts, templates=templates, form=form)
    return handle_content_type(response)
