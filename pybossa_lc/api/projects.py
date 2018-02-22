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

from ..forms import *
from ..cache import templates as templates_cache


auditlogger = AuditLogger(auditlog_repo, caller='web')
BLUEPRINT = Blueprint('projects', __name__)
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


def validate_parent(parent_id, presenter):
    """Validate a parent project."""
    if presenter != 'iiif-annotation':
        flash('Only IIIF annotation projects can be built from a parent',
              'error')
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
@BLUEPRINT.route('/<category_short_name>/new', methods=['GET', 'POST'])
def new(category_short_name):
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

    template_choices = [(t['id'], t['project']['name']) for t in templates]
    volume_choices = [(v['id'], v['name']) for v in volumes]
    parent_choices = [(p.id, p.name) for p in projects]
    parent_choices.append(('None', ''))

    form = ProjectForm(request.body)
    form.template_id.choices = template_choices
    form.volume_id.choices = volume_choices
    form.parent_id.choices = parent_choices

    built_templates = get_built_templates(category)

    if request.method == 'POST':
        if form.validate():
            tmpl = [t for t in templates
                    if t['id'] == form.template_id.data][0]
            volume = [v for v in volumes if v['id'] == form.volume_id.data][0]
            handle_valid_project_form(form, tmpl, volume, category,
                                      built_templates)

        else:
            flash('Please correct the errors', 'error')

    valid_parent_ids = get_valid_parent_project_ids(category)
    response = dict(form=form, templates=templates, volumes=volumes,
                    built_templates=built_templates,
                    valid_parent_ids=valid_parent_ids)
    return handle_content_type(response)


def handle_valid_project_form(form, template, volume, category,
                              built_templates):
    """Handle a seemingly valid project form."""
    presenter = category.info.get('presenter')
    task = template['task']
    if not task:
        flash('The selected template is incomplete', 'error')
        return

    # Get parent ID
    has_parent = form.parent_id.data and form.parent_id.data != 'None'
    parent_id = int(form.parent_id.data) if has_parent else None

    # Get the task import data
    import_data = {}
    if presenter == 'z3950':
        import_data = _get_flickr_data(volume)
    elif presenter == 'iiif-annotation':
        import_data = _get_iiif_annotation_data(volume, template['id'],
                                                parent_id)
    if not import_data:
        err_msg = "Invalid volume details for the task presenter type"
        flash(err_msg, 'error')
        return

    # Validate a parent
    if parent_id:
        validate_parent(parent_id, presenter)

    # Check for similar projects
    if volume['id'] in built_templates[template['id']]:
        err_msg = "A project already exists for that volume and template."
        flash(err_msg, 'error')
        return

    # Create
    webhook = '{0}libcrowds/analysis'.format(request.url_root)
    project = Project(name=form.name.data,
                      short_name=form.short_name.data,
                      description=template['project']['description'],
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'tutorial': template.get('tutorial', ''),
                          'volume_id': volume['id'],
                          'template_id': template['id'],
                          'tags': template.get('tags', {})
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
        n_answers = template['project'].get('min_answers', 3)
        task_repo.update_tasks_redundancy(project, n_answers)
        return redirect_content_type(url_for('home.home'))


def get_built_templates(category):
    """Get dict of templates against volumes for all current projects."""
    templates = templates_cache.get_by_category_id(category.id)
    built_templates = {tmpl['id']: [] for tmpl in templates}
    projects = project_repo.filter_by(category_id=category.id)
    for p in projects:
        tmpl_id = p.info.get('template_id')
        vol_id = p.info.get('volume_id')
        if tmpl_id and vol_id and tmpl_id in built_templates.keys():
            tmpl_vols = built_templates.get(tmpl_id, [])
            if vol_id not in tmpl_vols:
                tmpl_vols.append(vol_id)
                built_templates[tmpl_id] = tmpl_vols
    return built_templates


def get_valid_parent_project_ids(category):
    """Return a list of IDs for valid parent projects for the category."""
    valid_project_ids = []
    projects = project_repo.filter_by(category_id=category.id)
    presenter = category.info.get('presenter')
    if presenter == 'iiif-annotation':
        for p in projects:
            parent_tmpl_id = p.info.get('template_id')
            if not parent_tmpl_id:
                continue

            parent_tmpl = templates_cache.get_by_id(parent_tmpl_id)
            if not parent_tmpl or not parent_tmpl['task']:
                continue

            parent_task = parent_tmpl['task']
            if not parent_task.get('mode') == 'select':
                continue

            results = result_repo.filter_by(project_id=p.id)
            empty_results = [r for r in results if not r.info]
            incomplete_tasks = task_repo.filter_tasks_by(state='ongoing',
                                                         project_id=p.id)

            if not empty_results and not incomplete_tasks:
                valid_project_ids.append(p.id)
    return valid_project_ids
