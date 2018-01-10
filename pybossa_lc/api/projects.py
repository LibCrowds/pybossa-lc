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
    print n_tasks
    if n_tasks <= MAX_NUM_SYNCHRONOUS_TASKS_IMPORT:
        importer.create_tasks(task_repo, project.id, **import_data)
    else:
        IMPORT_QUEUE.enqueue(import_tasks, project.id, **import_data)
        return '''The project is being generated with a large amount of tasks.
            You will recieve an email when the process is complete.'''
    plural = 's' if n_tasks != 1 else ''
    return 'The project was generated with {} task{}.'.format(n_tasks, plural)


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
    name = '{0}: {1}'.format(template['project']['name'], volume['name'])
    badchars = r"([$#%·:,.~!¡?\"¿'=)(!&\/|]+)"
    short_name = re.sub(badchars, '', name.lower().strip()).replace(' ', '_')
    return name, short_name


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


@login_required
@BLUEPRINT.route('/<category_short_name>/create', methods=['POST'])
def create(category_short_name):
    """Create a LibCrowds project for a given category."""
    category = project_repo.get_category_by(short_name=category_short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('create', Project)
    templates = templates_cache.get_by_category_id(category.id)
    volumes = category.info.get('volumes', [])
    projects = project_repo.filter_by(category_id=category.id)

    # Check for a valid task presenter
    presenter = category.info.get('presenter')
    if presenter not in ['z3950', 'iiif-annotation']:
        err_msg = 'Invalid task presenter, please contact an administrator'
        flash(err_msg, 'error')
        return redirect_content_type(url_for('home.home'))

    # Set the options for the form
    template_choices = [(t['id'], t['project']['name']) for t in templates]
    volume_choices = [(v['id'], v['name']) for v in volumes]
    parent_choices = [(p.id, p.name) for p in projects]
    parent_choices.append(('None', 0))
    form = ProjectForm(request.body)
    form.template_id.choices = template_choices
    form.volume_id.choices = volume_choices
    form.parent_id.choices = parent_choices

    # Remove parent ID field if not set or Z39.50 presenter
    if not form.parent_id.data or presenter != 'iiif-annotation':
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
            err_msg = "Invalid volume details for the task presenter type"
            flash(err_msg, 'error')
            return redirect_content_type(url_for('home.home'))

        webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root,
                                                     presenter)
        existing_project = project_repo.filter_by(short_name=short_name)
        if existing_project:
            err_msg = "A project already exists with that short name."
            flash(err_msg, 'error')
            return redirect_content_type(url_for('home.home'))

        project = Project(name=name,
                          short_name=short_name,
                          description=tmpl['project']['description'],
                          long_description='',
                          owner_id=current_user.id,
                          info={
                              'tutorial': tmpl.get('tutorial', ''),
                              'volume_id': volume['id'],
                              'template_id': tmpl['id'],
                              'tags': tmpl.get('tags', {})
                          },
                          webhook=webhook,
                          category_id=category.id,
                          owners_ids=[current_user.id])
        project_repo.save(project)

        # Attempt to generate the tasks
        success = True
        try:
            msg = _import_tasks(project, **import_data)
            flash(msg, 'success')
        except BulkImportException as err_msg:
            success = False
            project_repo.delete(project)
            flash(err_msg, 'error')

        except Exception as inst:  # pragma: no cover
            success = False
            current_app.logger.error(inst)
            print inst
            project_repo.delete(project)
            msg = 'Uh oh, an error was encountered while generating the tasks'
            flash(msg, 'error')

        if success:
            auditlogger.add_log_entry(None, project, current_user)
            task_repo.update_tasks_redundancy(project, 3)
            project.published = True
            project_repo.save(project)
            return redirect_content_type(url_for('home.home'))

    elif request.method == 'POST':
        flash('Please correct the errors', 'error')

    response = dict(form=form)
    return handle_content_type(response)
