# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

import re
import json
from flask import Response, Blueprint, flash, request, abort, current_app
from flask import jsonify
from flask.ext.login import login_required, current_user
from pybossa.core import csrf, project_repo
from pybossa.model.project import Project
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer
from pybossa.core import auditlog_repo, task_repo, result_repo
from pybossa.importers import BulkImportException
from pybossa.util import handle_content_type, redirect_content_type, url_for
from pybossa.default_settings import TIMEOUT
from pybossa.jobs import import_tasks
from pybossa.auditlogger import AuditLogger
from wtforms import TextField
from pybossa.jobs import enqueue_job

from .. import project_tmpl_repo
from ..forms import *


auditlogger = AuditLogger(auditlog_repo, caller='web')
BLUEPRINT = Blueprint('lc_projects', __name__)
MAX_NUM_SYNCHRONOUS_TASKS_IMPORT = 300


def _import_tasks(project, **import_data):
    """Import the tasks."""
    n_tasks = importer.count_tasks_to_import(**import_data)
    if n_tasks <= MAX_NUM_SYNCHRONOUS_TASKS_IMPORT:
        importer.create_tasks(task_repo, project.id, **import_data)
    else:
        job = dict(name=import_tasks,
                   args=[project.id],
                   kwargs=import_data,
                   timeout=current_app.config.get('TIMEOUT'),
                   queue='medium')
        enqueue_job(job)
        return '''The project is being generated with a large amount of tasks.
            You will recieve an email when the process is complete.'''
    plural = 's' if n_tasks != 1 else ''
    return 'The project was generated with {} task{}.'.format(n_tasks, plural)


def validate_parent(parent_id, template):
    """Validate a parent project."""
    parent = project_repo.get(parent_id)
    parent_tmpl_id = template.get('parent_template_id')
    if not parent_tmpl_id:
        flash('This template should not be built from a parent', 'error')
        return False

    if parent.info.get('template_id') != parent_tmpl_id:
        flash('Parent is not of the correct template type', 'error')
        return False

    empty_results = result_repo.filter_by(info=None, project_id=parent_id)
    if empty_results:
        flash('Parent contains incomplete results', 'error')
        return False

    incomplete_tasks = task_repo.filter_tasks_by(state='ongoing',
                                                 project_id=parent_id)
    if incomplete_tasks:
        flash('Parent contains incomplete tasks', 'error')
        return False

    return True


@login_required
@BLUEPRINT.route('/<category_short_name>/new', methods=['GET', 'POST'])
def new(category_short_name):
    """Create a LibCrowds project for a given category."""
    category = project_repo.get_category_by(short_name=category_short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('create', Project)

    enhanced_tmpls = get_enhanced_templates(category)
    volumes = category.info.get('volumes', [])
    projects = project_repo.filter_by(category_id=category.id)

    # Check for a valid task presenter
    presenter = category.info.get('presenter')
    if presenter not in ['z3950', 'iiif-annotation']:
        err_msg = 'Invalid task presenter, please contact an administrator'
        flash(err_msg, 'error')
        return redirect_content_type(url_for('home.home'))

    form = ProjectForm(request.body)

    volume_choices = [(v['id'], v['name']) for v in volumes]
    form.volume_id.choices = volume_choices

    parent_choices = [(p.id, p.name) for p in projects]
    parent_choices.append(('None', ''))
    form.parent_id.choices = parent_choices

    template_choices = [(tmpl['id'], tmpl['name']) for tmpl in enhanced_tmpls]
    form.template_id.choices = template_choices

    if request.method == 'POST':
        if form.validate():
            tmpl = project_tmpl_repo.get(form.template_id.data)
            volume = [v for v in volumes if v['id'] == form.volume_id.data][0]
            handle_valid_project_form(form, tmpl, volume, category)

        else:
            flash('Please correct the errors', 'error')

    response = dict(form=form, templates=enhanced_tmpls, volumes=volumes)
    return handle_content_type(response)


def handle_valid_project_form(form, template, volume, category):
    """Handle a valid project form."""
    presenter = category.info.get('presenter')
    task = template.task
    if not task:
        flash('The selected template is incomplete', 'error')
        return

    # Create
    webhook = '{0}lc/analysis'.format(request.url_root)
    project = Project(name=form.name.data,
                      short_name=form.short_name.data,
                      description=template.description,
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'volume_id': volume['id'],
                          'template_id': template.id
                      },
                      webhook=webhook,
                      published=True,
                      category_id=category.id,
                      owners_ids=[current_user.id])
    project_repo.save(project)

    # Attempt to generate the tasks
    success = True
    import_data = volume.get('data', {})
    import_data['type'] = volume.get('importer')
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
        task_repo.update_tasks_redundancy(project, template.min_answers)
        return redirect_content_type(url_for('home.home'))


def get_enhanced_templates(category):
    """Get templates with details of available volumes and parents for each."""
    templates = project_tmpl_repo.get_by_category_id(category.id)
    volumes = category.info.get('volumes', [])
    projects = project_repo.filter_by(category_id=category.id)

    # Remove incomplete templates
    tmpl_dicts = [tmpl.to_dict() for tmpl in templates if tmpl.task]

    for tmpl in tmpl_dicts:
        # Add available volumes
        available_vols = [vol['id'] for vol in volumes[:]]
        for project in projects:
            tmpl_id = project.info.get('template_id')
            if tmpl_id != tmpl['id']:
                continue

            vol_id = project.info.get('volume_id')
            available_vols = filter(lambda x: x != vol_id, available_vols)

        tmpl['available_volumes'] = available_vols

    return tmpl_dicts
