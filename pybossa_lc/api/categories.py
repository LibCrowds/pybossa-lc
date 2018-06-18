# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import time
import uuid
import pandas
from flask import Blueprint, flash, request, abort, current_app, url_for
from flask.ext.login import login_required, current_user
from pybossa.util import handle_content_type, get_avatar_url
from pybossa.util import redirect_content_type
from pybossa.core import project_repo
from pybossa.core import uploader, importer
from pybossa.auth import ensure_authorized_to
from pybossa.forms.forms import AvatarUploadForm, GenericBulkTaskImportForm
from pybossa.importers import BulkImportException
from pybossa.cache import project_stats

from ..utils import *
from ..forms import VolumeForm


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


@BLUEPRINT.route('/<short_name>/progress')
def progress(short_name):
    """Return progress for each volume and template."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    tmpl_index = {t['id']: t for t in category.info.get('templates', [])}
    vol_index = {v['id']: v for v in category.info.get('volumes', [])}
    data = {v_id: {t_id: 0 for t_id in tmpl_index} for v_id in vol_index}
    projects = project_repo.filter_by(category_id=category.id)
    for project in projects:
        ps = project_stats.get_stats(project.id, full=True)
        try:
            row = data[project.info['volume_id']]
            row[project.info['template_id']] = ps.overall_progress
        except KeyError:
            continue

    # Replace IDs with names and flatten
    flat_data = []
    for vol_id in data:
        row = {'Volume': vol_index[vol_id]['name']}
        for tmpl_id in data[vol_id]:
            tmpl_name = tmpl_index[tmpl_id]['name']
            if tmpl_name == 'Volume':
                tmpl_name = '_Volume'
            row[tmpl_name] = data[vol_id][tmpl_id]
        flat_data.append(row)

    if request.args.get('csv'):
        df = pandas.DataFrame(flat_data)
        df.set_index('Volume', inplace=True)
        csv = df.to_csv(encoding='utf8')
        response = dict(progress=csv)
        return handle_content_type(response)

    response = dict(progress=flat_data)
    return handle_content_type(response)


@BLUEPRINT.route('/<short_name>/tags')
@BLUEPRINT.route('/<short_name>/project-tags')
@BLUEPRINT.route('/<short_name>/project-filters')
def project_tags(short_name):
    """Return all filters currently associated with the category's projects."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    projects = project_repo.filter_by(category_id=category.id)
    all_filters = [(k, v) for project in projects
                   for k, v in project.info.get('filters', {}).items()]

    filters = {}
    for _filter in all_filters:
        key = _filter[0]
        value = _filter[1]
        filter_opts = filters.get(key, [])
        filter_opts.append(value)
        filter_opts = list(set(filter_opts))
        filters[key] = filter_opts

    response = dict(filters=filters)
    return handle_content_type(response)
