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
from pybossa.core import importer, sentinel
from pybossa.core import auditlog_repo, task_repo, result_repo
from pybossa.importers import BulkImportException
from pybossa.util import handle_content_type, redirect_content_type, url_for
from pybossa.default_settings import TIMEOUT
from pybossa.jobs import import_tasks
from pybossa.auditlogger import AuditLogger

from ..utils import get_template, get_volume
from ..forms import ProjectForm
from ..cache import templates as templates_cache


auditlogger = AuditLogger(auditlog_repo, caller='web')
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
@BLUEPRINT.route('/create/<int:category_id>', methods=['POST'])
def create(category_id):
    """Create a LibCrowds project for a given category."""
    category = project_repo.get_category(category_id)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('create', Project)
    templates = templates_cache.get_by_category_id(category.id)
    volumes = category.info.get('volumes', [])
    projects = project_repo.get_by(category_id=category.id)

    # Check for a valid task presenter
    presenter = category.info.get('presenter')
    if presenter not in ['z3950', 'iiif-annotation']:
        err_msg = 'Invalid task presenter, please contact an administrator'
        flash(err_msg, 'error')
        return redirect_content_type(url_for('home.home'))

    # Set the options for the form
    template_choices = [(t['id'], t['project']['name']) for t in templates]
    volume_choices = [(v['id'], v['name']) for v in volumes]
    project_choices = [(p.id, p.name) for p in projects]
    form = ProjectForm(request.body)
    form.template_id.choices = template_choices
    form.volume_id.choices = volume_choices
    form.parent_id.choices = project_choices

    # Remove parent ID field for Z39.50 presenter
    if presenter == 'z3950':
        del form.parent_id

    if request.method == 'POST' and form.validate():
        tmpl = [t for t in templates if t['id'] == form.template_id.data][0]
        volume = [v for v in volumes if v['id'] == form.volume_id.data][0]
        name, short_name = get_name_and_shortname(tmpl, volume)

        # Get the task import data
        import_data = {}
        if presenter == 'z3950':
            import_data = _get_flickr_data(volume)
        elif presenter == 'iiif-annotation':
            import_data = _get_iiif_annotation_data(volume, tmpl['id'],
                                                    form.parent_id)

        if not import_data:
            msg = """Invalid volume details for the task presenter type,
                  please contact an administrator"""
            return redirect_content_type(url_for('home.home'))

        webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root,
                                                     presenter)
        existing_project = project_repo.filter_by(short_name=short_name)
        if existing_project:
            msg = "A project already exists with that short name."
            return json_response(msg, 'error')

        project = Project(name=name,
                          short_name=short_name,
                          description=tmpl['description'],
                          long_description='',
                          owner_id=current_user.id,
                          info={
                              'tutorial': tmpl.get('tutorial'),
                              'volume_id': volume['id'],
                              'template_id': tmpl['id'],
                              'tags': tmpl.get('tags', {})
                          },
                          webhook=webhook,
                          category_id=category.id,
                          owners_ids=[current_user.id])
        project_repo.save(project)

        # Attempt to generate the tasks
        msg = ''
        success = True
        try:
            response = _import_tasks(project, **import_data)
        except BulkImportException as err_msg:
            success = False
            project_repo.delete(project)
            flash(err_msg, 'error')

        except Exception as inst:  # pragma: no cover
            success = False
            current_app.logger.error(inst)
            project_repo.delete(project)
            msg = 'Uh oh, an error was encountered while generating the tasks'
            flash(msg, 'error')

        if success:
            auditlogger.add_log_entry(None, project, current_user)
            task_repo.update_tasks_redundancy(project, 3)
            project.published = True
            project_repo.save(project)
            flash(msg, 'success')
            return redirect_content_type(url_for('home.home'))

    elif request.method == 'POST':
        flash('Please correct the errors', 'error')

    response = dict(form=form)
    return handle_content_type(response)


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
