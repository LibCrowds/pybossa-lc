# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

import re
import json
from flask import Response, Blueprint, flash, request, abort, current_app
from flask.ext.login import login_required, current_user
from rq import Queue
from pybossa.core import csrf, project_repo
from pybossa.model.project import Project
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer, sentinel, task_repo
from pybossa.importers import BulkImportException
from pybossa.util import handle_content_type
from pybossa.default_settings import TIMEOUT
from pybossa.jobs import import_tasks


BLUEPRINT = Blueprint('projects', __name__)
MAX_NUM_SYNCHRONOUS_TASKS_IMPORT = 1000
IMPORT_QUEUE = Queue('medium', connection=sentinel.master,
                     default_timeout=TIMEOUT)


def _import_tasks(project, name, short_name, **import_data):
    """Import the tasks."""
    number_of_tasks = importer.count_tasks_to_import(**import_data)
    if number_of_tasks <= MAX_NUM_SYNCHRONOUS_TASKS_IMPORT:
        importer.create_tasks(task_repo, project.id, **import_data)
    else:
        IMPORT_QUEUE.enqueue(import_tasks, project.id, **import_data)
        msg = '''The project is being generated with a large amount of tasks.
            You will recieve an email when the process is complete.'''
        return json_response(msg, 'info', name, short_name)
    msg = '''The project has been generated successfully.'''
    return json_response(msg, 'success', name, short_name)


def _get_name_and_shortname(template, volume):
    """Create a name and shortname from the template and volume details."""
    name = '{0}: {1}'.format(template['name'], volume['name'])
    badchars = r"([$#%·:,.~!¡?\"¿'=)(!&\/|]+)"
    short_name = re.sub(badchars, '', name.lower().strip()).replace(' ', '_')
    return name, short_name


def json_response(msg, status, name, short_name):
    """Return a message as a JSON response."""
    res = dict(status=status, flash=msg, name=name, short_name=short_name)
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

    name, short_name = _get_name_and_shortname(template, volume)

    # Get the task import data for different presenter types
    import_data = {}
    presenter = data['collection']['info'].get('presenter')
    if presenter == 'z3950':
        import_data = _get_flickr_data(volume)
    elif presenter == 'iiif-annotation':
        import_data = _get_iiif_annotation_data(volume, template)
    else:
        msg = 'Unknown task presenter: {}'.format(presenter)
        return json_response(msg, 'error', name, short_name)
    if not import_data:
        msg = "Invalid volume details for the collection's task presenter type"
        return json_response(msg, 'error', name, short_name)

    ensure_authorized_to('create', Project)

    presenter = collection['info']['presenter']
    webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root, presenter)

    existing_project = project_repo.filter_by(short_name=short_name)
    if existing_project:
        msg = """A project already exists with that short name, which usually
            means that a project has already been created from the selected
            volume and template."""
        return json_response(msg, 'error', name, short_name)

    project = Project(name=name,
                      short_name=short_name,
                      description=template['description'],
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'tutorial': template.get('tutorial'),
                          'volume': volume,
                          'template': template,
                          'tags': data.get('tags')
                      },
                      webhook=webhook,
                      category_id=category.id,
                      owners_ids=[current_user.id])

    project_repo.save(project)

    msg = ''
    try:
        return _import_tasks(project, name, short_name, **import_data)
    except BulkImportException as err_msg:
        msg = err_msg
        return json_response(err_msg, 'error', name, short_name)
    except Exception as inst:  # pragma: no cover
        current_app.logger.error(inst)
        msg = 'Uh oh, an error was encountered while generating the tasks'

    # Clean up if something went wrong
    project_repo.delete(project)
    return json_response(msg, 'error', name, short_name)


@csrf.exempt
@login_required
@BLUEPRINT.route('/check-shortname', methods=['POST'])
def check_shortname():
    required_args = ['volume', 'template']
    data = json.loads(request.data)
    if not all(arg in data for arg in required_args):
        abort(400)

    volume = data['volume']
    template = data['template']
    name, short_name = _get_name_and_shortname(template, volume)
    projects = project_repo.filter_by(short_name=short_name)
    if projects:
        msg = 'Shortname already exists'
        return json_response(msg, 'error', name, short_name)
    msg = 'Shortname does not exist'
    return json_response(msg, 'success', name, short_name)
