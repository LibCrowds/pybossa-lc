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
from pybossa.core import csrf
from pybossa.auth import ensure_authorized_to
from pybossa.forms.forms import AvatarUploadForm, GenericBulkTaskImportForm
from pybossa.importers import BulkImportException

from ..utils import *
from ..forms import VolumeForm, CustomExportForm
from ..exporters.csv_anno_exporter import CsvAnnotationExporter
from ..exporters.json_anno_exporter import JsonAnnotationExporter


BLUEPRINT = Blueprint('lc_categories', __name__)


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

    new_vol = None
    if request.method == 'POST' and form.validate():
        volume_id = str(uuid.uuid4())
        new_vol = dict(id=volume_id,
                       name=form.name.data,
                       short_name=form.short_name.data,
                       importer=form.importer.data)
        volumes.append(new_vol)
        category.info['volumes'] = volumes
        project_repo.update_category(category)
        flash("Volume added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(form=form, new_volume=new_vol, all_importers=all_importers)
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
    import_form = GenericBulkTaskImportForm()(volume['importer'],
                                              **volume.get('data', {}))

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

    cat_projects = project_repo.filter_by(category_id=category.id)
    has_projects = len([p for p in cat_projects
                        if p.info.get('volume_id') == volume_id]) > 0

    if request.method == 'POST':
        # Process task import form
        if (request.form.get('btn') == 'Import' or
                request.body.get('btn') == 'Import'):

            import_form = GenericBulkTaskImportForm()(volume['importer'],
                                                      request.body)
            if import_form.validate():
                if has_projects:
                    flash('Update failed as projects have already been built',
                          'error')
                else:
                    volume['data'] = import_form.get_import_data()
                    import_data = import_form.get_import_data()
                    try:
                        importer.count_tasks_to_import(**import_data)
                        update()
                        flash('Volume updated', 'success')
                    except BulkImportException as err:
                        flash(err.message, 'error')

            else:
                flash('Please correct the errors', 'error')

        # Process volume details form
        elif request.form.get('btn') != 'Upload':
            form = VolumeForm(request.body)
            all_importers = importer.get_all_importer_names()
            form.importer.choices = [(name, name) for name in all_importers]

            if form.validate():
                if has_projects:
                    flash('Update failed as projects have already been built',
                          'error')
                else:
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
                    volume=volume, has_projects=has_projects)
    return handle_content_type(response)


@BLUEPRINT.route('/<short_name>/export')
def export_collection_data(short_name):
    """Export collection data."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    motivation = request.args.get('type')
    fmt = request.args.get('format')
    if not (motivation and fmt):
        abort(404)

    if fmt not in ['csv', 'json']:
        abort(415)

    if motivation not in ['describing', 'tagging', 'commenting']:
        abort(415)

    def respond_json(export_fmt_id):
        json_custom_exporter = JsonAnnotationExporter()
        res = json_custom_exporter.response_zip(category, export_fmt_id)
        return res

    def respond_csv(export_fmt_id):
        csv_custom_exporter = CsvAnnotationExporter()
        res = csv_custom_exporter.response_zip(category, export_fmt_id)
        return res

    return {"json": respond_json, "csv": respond_csv}[fmt](motivation)


@BLUEPRINT.route('/<short_name>/project-tags')
def project_tags(short_name):
    """Return all tags currently associated with the category's projects."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    projects = project_repo.filter_by(category_id=category.id)
    tags = [(k, v) for project in projects
                    for k, v in project.info.get('tags', {}).items()]

    tags = {}
    for tag in tags:
        key = tag[0]
        value = tag[1]
        tag_values = tags.get(key, [])
        tag_values.append(value)
        tag_values = list(set(tag_values))
        tags[key] = tag_values

    response = dict(tags=tags)
    return handle_content_type(response)


@BLUEPRINT.route('/<short_name>/tags')
def search_item_tags(short_name):
    """Search for item tags

    We'll want to move the to a proper annotations server in future, but for
    now just store them as part of the category object.
    """
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    tags = category.info.get('tmp_tag_annotations', [])

    query = request.args.get('query')
    target = request.args.get('target')

    if query:
        tags = [t for t in tags if query in t['body']['value']]

    if target:
        tags = [t for t in tags if target in t['target']]

    response = dict(tags=tags)
    return handle_content_type(response)


@csrf.exempt
@BLUEPRINT.route('/<short_name>/tags/add', methods=['GET', 'POST'])
def add_item_tag(short_name):
    """Tag an item.

    We'll want to move the to a proper annotations server in future, but for
    now just store them as part of the category object.
    """
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    tag = None

    if request.method == 'POST':
        data = json.loads(request.data)
        target = data.get('target')
        typ = data.get('type')
        value = data.get('value')
        if not target or not value or not typ:
            abort(400)

        if typ not in ['image', 'iiif']:
            abort(415)

        if typ == 'image':
            target = {
                "id": target,
                "type": "Image"
            }

        tags = category.info.get('tmp_tag_annotations', [])

        try:
            idx = [i for i, _tag in enumerate(tags)
                   if _tag['body']['value'] == value][0]
            tag = tags[idx]
        except IndexError:
            idx = -1
            tag = {
                "@context": "http://www.w3.org/ns/anno.jsonld",
                "type": "Annotation",
                "id": str(uuid.uuid4()),
                "motivation": "tagging",
                "body": {
                    "type": "TextualBody",
                    "value": value,
                    "format" : "text/plain"
                },
                "target": []
            }

        tag_has_target = [tgt for tgt in tag['target'] if tgt == target]
        if not tag_has_target:
            tag['target'].append(target)
            if idx >= 0:
                tags[idx] = tag
            else:
                tags.append(tag)
            category.info['tmp_tag_annotations'] = tags
            project_repo.update_category(category)
            flash("Tag added", 'success')
        else:
            flash("Tag already exists", 'info')

    response = dict(tag=tag)
    return handle_content_type(response)
