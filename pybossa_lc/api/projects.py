# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

import re
import json
from flask import Response, Blueprint, flash, request, abort, current_app
from flask import jsonify
from flask.ext.login import login_required, current_user
from rq import Queue
from pybossa.core import csrf, project_repo
from pybossa.model.project import Project
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer, sentinel, task_repo, result_repo
from pybossa.importers import BulkImportException
from pybossa.util import handle_content_type
from pybossa.default_settings import TIMEOUT
from pybossa.jobs import import_tasks


BLUEPRINT = Blueprint('projects', __name__)
MAX_NUM_SYNCHRONOUS_TASKS_IMPORT = 300
IMPORT_QUEUE = Queue('medium', connection=sentinel.master,
                     default_timeout=TIMEOUT)


def _import_tasks(project, **import_data):
    """Import the tasks."""
    n_tasks = importer.count_tasks_to_import(**import_data)
    if n_tasks <= MAX_NUM_SYNCHRONOUS_TASKS_IMPORT:
        importer.create_tasks(task_repo, project.id, **import_data)
    else:
        IMPORT_QUEUE.enqueue(import_tasks, project.id, **import_data)
        return '''The project is being generated with a large amount of tasks.
            You will recieve an email when the process is complete.'''
    return 'The project was generated with {} tasks.'.format(n_tasks)


def get_template(category, template_id):
    """Return a valid template."""
    templates = category.info.get('templates', {})
    template = templates.get(template_id)
    if not template:
        msg = 'Template not found'
        abort(jsonify(message=msg), 404)
    return template


def get_volume(category, volume_id):
    """Return a valid volume."""
    volumes = category.info.get('volumes', {})
    volume = volumes.get(volume_id)
    if not volume:
        msg = 'Volume not found'
        abort(jsonify(message=msg), 404)
    return volume


def get_parent(parent_id, template):
    """Return a valid parent."""
    if not parent_id:
        return None

    if not 'iiif-annotation' or template['mode'] != 'transcribe':
        msg = "Only IIIF transcription projects can be built from a parent"
        abort(jsonify(message=msg), 400)

    parent = project_repo.get(parent_id)
    if not parent:
        msg = "Parent not found"
        abort(jsonify(message=msg), 400)

    empty_results = result_repo.filter_by(info=None, project_id=parent.id)
    if empty_results:
        msg = "Parent contains incomplete results"
        abort(jsonify(message=msg), 400)

    incomplete_tasks = task_repo.filter_by(status='ongoing',
                                            project_id=parent.id)
    if incomplete_tasks:
        msg = "Parent contains incomplete tasks"
        abort(jsonify(message=msg), 400)

    return parent


def get_name_and_shortname(template, volume):
    """Create a name and shortname from the template and volume details."""
    name = '{0}: {1}'.format(template['name'], volume['name'])
    badchars = r"([$#%·:,.~!¡?\"¿'=)(!&\/|]+)"
    short_name = re.sub(badchars, '', name.lower().strip()).replace(' ', '_')
    return name, short_name


def json_response(msg, status, project={}):
    """Return a message as a JSON response."""
    res = dict(status=status, flash=msg, project=project)
    return Response(json.dumps(res), 200, mimetype='application/json')


def _get_iiif_annotation_data(volume, template_id, parent_id):
    """Return IIIF manifest data."""
    pattern = r'^(https?:\/\/).*\/manifest\.json$'
    source = volume.get('source', '')
    match = re.search(pattern, source)
    if match:
        return dict(type='iiif-annotation', manifest_uri=source,
                    template_id=template_id, parent_id=parent_id)


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
    required_args = ['category_id', 'volume_id', 'template_id', 'parent_id']
    data = json.loads(request.data)
    if not all(arg in data for arg in required_args):
        msg = 'Missing required arguments'
        abort(jsonify(message=msg), 400)

    category = project_repo.get_category(data['category_id'])
    if not category:
        msg = 'Category not found'
        abort(jsonify(message=msg), 404)

    volume = get_volume(category, data['volume_id'])
    template = get_template(category, data['template_id'])
    parent = get_parent(data['parent_id'], template)

    name, short_name = get_name_and_shortname(template, volume)

    # Get the task import data for different presenter types
    import_data = {}
    presenter = data['collection']['info'].get('presenter')
    if presenter == 'z3950':
        import_data = _get_flickr_data(volume)
    elif presenter == 'iiif-annotation':
        import_data = _get_iiif_annotation_data(volume, template, parent)
    else:
        msg = 'Unknown task presenter: {}'.format(presenter)
        return json_response(msg, 'error')
    if not import_data:
        msg = "Invalid volume details for the collection's task presenter type"
        return json_response(msg, 'error')

    ensure_authorized_to('create', Project)

    presenter = category.info['presenter']
    webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root, presenter)

    existing_project = project_repo.filter_by(short_name=short_name)
    if existing_project:
        msg = "A project already exists with that short name."
        return json_response(msg, 'error')

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
        response = _import_tasks(project, **import_data)
    except BulkImportException as err_msg:
        project_repo.delete(project)
        return json_response(err_msg, 'error')
    except Exception as inst:  # pragma: no cover
        current_app.logger.error(inst)
        msg = 'Uh oh, an error was encountered while generating the tasks'
        project_repo.delete(project)
        return json_response(msg, 'error')

    response['project'] = project

    # Update redundancy and publish the project if generated successfully
    task_repo.update_tasks_redundancy(project, 3)
    project.published = True
    project_repo.save(project)
    return json_response(msg, 'success', project)


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
    _name, short_name = get_name_and_shortname(template, volume)
    projects = project_repo.filter_by(short_name=short_name)
    if projects:
        return Response(json.dumps(projects[0]), 200,
                        mimetype='application/json')
    return Response(json.dumps({}), 200, mimetype='application/json')
