# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

import re
import json
from flask import Response, Blueprint, flash, request, abort, current_app
from pybossa.core import csrf, project_repo
from pybossa.model.project import Project
from flask.ext.login import login_required, current_user
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer
from pybossa.importers import BulkImportException
from pybossa.view.projects import _import_tasks
from pybossa.util import handle_content_type


BLUEPRINT = Blueprint('projects', __name__)


def json_response(msg, status):
    """Return a message as a JSON response."""
    res = dict(status=status, msg=msg)
    return Response(json.dumps(res), 200, mimetype='application/json')


def _get_iiif_annotation_data(volume, template):
    """Return IIIF manifest data."""
    pattern = r'^(https?:\/\/).*\/manifest\.json$'
    source = volume.get('source', '')
    match = re.search(pattern, source)
    if match:
        return dict(type='iiif-annotation', manifest_uri=source,
                    template=template)


def _get_flickr_data(volume):
    """Return Flickr data."""
    pattern = r'(?<=albums/)\d+(?=/|$)'
    source = volume.get('source', '').strip()
    match = re.search(pattern, source)
    if match:
        return dict(type='flickr', album_id=match.group(0))


@csrf.exempt
@login_required
@BLUEPRINT.route('/create', methods=['POST'])
def create():
    """Create a LibCrowds project."""
    required_args = ['collection', 'volume', 'template']
    data = json.loads(request.data)
    if not all(arg in data for arg in required_args):
        abort(400)

    volume = data['volume']
    template = data['template']
    collection = data['collection']
    category = project_repo.get_category(collection.get('id'))
    if not category:
        abort(404)

    # Get the task import data for different presenter types
    import_data = {}
    presenter = data['collection'].get('presenter')
    if presenter == 'z3950':
        import_data = _get_flickr_data(volume)
    elif presenter == 'iiif-annotation':
        import_data = _get_iiif_annotation_data(volume, template)
    else:
        return json_response('Invalid task presenter', 'error')
    if not import_data:
        msg = "Invalid volume details for the collection's task presenter type"
        return json_response(msg, 'error')

    ensure_authorized_to('create', Project)

    name = '{0}: {1}'.format(template['name'], volume['name'])
    badchars = r"([$#%·:,.~!¡?\"¿'=)(!&\/|]+)"
    short_name = re.sub(badchars, '', name.lower().strip()).replace(' ', '_')
    presenter = collection['info']['presenter']
    webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root, presenter)

    existing_project = project_repo.filter_by(short_name=short_name)
    if existing_project:
        msg = """A project already exists with that short name, which usually
            means that a project has already been created from the selected
            volume and template."""
        return json_response(msg, 'error')

    project = Project(name=name,
                      short_name=short_name,
                      description=template['description'],
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'volume': volume,
                          'template': template
                      },
                      webhook=webhook,
                      category_id=category.id,
                      owners_ids=[current_user.id])

    project_repo.save(project)

    try:
        return _import_tasks(project, **import_data)
    except BulkImportException as err_msg:
        flash(err_msg, 'error')
    except Exception as inst:  # pragma: no cover
        current_app.logger.error(inst)
    msg = 'Oops! Looks like there was an error!'
    return json_response(msg, 'error')
