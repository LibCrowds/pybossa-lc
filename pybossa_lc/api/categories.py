# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import time
import uuid
from flask import Blueprint, flash, request, abort, current_app
from flask.ext.login import login_required, current_user
from pybossa.util import handle_content_type, get_avatar_url
from pybossa.core import project_repo
from pybossa.core import uploader
from pybossa.auth import ensure_authorized_to
from pybossa.forms.forms import AvatarUploadForm

from ..forms import VolumeForm

BLUEPRINT = Blueprint('categories', __name__)


@login_required
@BLUEPRINT.route('/<short_name>/volumes/new', methods=['GET', 'POST'])
def new(short_name):
    """Add a volume."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    form = VolumeForm(request.body)

    if request.method == 'POST' and form.validate():
        volumes = category.info.get('volumes', [])
        if not isinstance(volumes, list):  # Clear old volumes dict
            volumes = []
        volume_id = str(uuid.uuid4())
        new_volume = dict(id=volume_id,
                          source=form.source.data,
                          name=form.name.data,
                          media_url=None)
        volumes.append(new_volume)
        category.info['volumes'] = volumes
        project_repo.update_category(category)
        flash("Volume added", 'success')
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<short_name>/volumes/<volume_id>/update',
                 methods=['GET', 'POST'])
def update(short_name, volume_id):
    """Update a volume."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', category)
    volumes = category.info.get('volumes', [])

    try:
        volume = [v for v in volumes if v['id'] == volume_id]
    except IndexError:
        abort(404)

    form = VolumeForm(data=volume)
    upload_form = AvatarUploadForm()

    def update_volume():
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
                volume['name'] = form.data.name
                volume['source'] = form.data.name
                update_volume()
            flash('Please correct the errors', 'error')
        else:
            if upload_form.validate_on_submit():
                _file = request.files['thumbnail']
                coordinates = (upload_form.x1.data, upload_form.y1.data,
                               upload_form.x2.data, upload_form.y2.data)
                prefix = time.time()
                _file.filename = "volume_{}.png".format(volume['id'])
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
                update_volume()
                project_repo.save_category(category)
                flash('Thumbnail updated', 'success')
            else:
                flash('You must provide a file', 'error')

    response = dict(form=form)
    return handle_content_type(response)
