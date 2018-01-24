# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

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

from ..utils import get_enhanced_volumes, get_projects_with_unknown_volumes
from ..forms import VolumeForm

BLUEPRINT = Blueprint('categories', __name__)


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

    response = dict(volumes=category_vols, unknown_projects=unknown_projects)
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
                       media_url=None)
        volumes.append(new_vol)
        category.info['volumes'] = volumes
        project_repo.update_category(category)
        flash("Volume added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(form=form, volumes=volumes)
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

    response = dict(form=form, upload_form=upload_form)
    return handle_content_type(response)
