# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

from flask import Blueprint, flash, request, abort, current_app
from flask.ext.login import login_required, current_user
from pybossa.model.project import Project
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer, db
from pybossa.core import auditlog_repo, task_repo, result_repo, project_repo
from pybossa.importers import BulkImportException
from pybossa.util import handle_content_type, redirect_content_type, url_for
from pybossa.jobs import import_tasks
from pybossa.auditlogger import AuditLogger
from pybossa.jobs import enqueue_job
from sqlalchemy import text

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


@login_required
@BLUEPRINT.route('/<category_short_name>/new', methods=['GET', 'POST'])
def new(category_short_name):
    """Create a LibCrowds project for a given category."""
    category = project_repo.get_category_by(short_name=category_short_name)
    if not category:  # pragma: no cover
        abort(404)

    ensure_authorized_to('create', Project)
    templates = category.info.get('templates', [])
    volumes = category.info.get('volumes', [])

    # Check for a valid task presenter
    presenter = category.info.get('presenter')
    if presenter not in ['z3950', 'iiif-annotation']:
        err_msg = 'Invalid task presenter, please contact an administrator'
        flash(err_msg, 'error')
        return redirect_content_type(url_for('home.home'))

    form = ProjectForm(request.body)
    volume_choices = [(v['id'], v['name']) for v in volumes]
    form.volume_id.choices = volume_choices
    template_choices = [(tmpl['id'], tmpl['name']) for tmpl in templates]
    form.template_id.choices = template_choices
    if request.method == 'POST':
        if form.validate():
            tmpl = [t for t in templates
                    if t['id'] ==  form.template_id.data][0]
            volume = [v for v in volumes if v['id'] == form.volume_id.data][0]
            handle_valid_project_form(form, tmpl, volume, category)

        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    built_projects = get_built_projects(category)
    response = dict(form=form, built_projects=built_projects)
    return handle_content_type(response)


def handle_valid_project_form(form, template, volume, category):
    """Handle a valid project form."""
    import_data = volume.get('data', {})
    import_data['type'] = volume.get('importer')

    # Use enhanced IIIF importer for IIIF projects
    if import_data['type'] == 'iiif':
        import_data['type'] = 'iiif-enhanced'

    # Check for parent
    if template['parent_template_id']:
        if volume.get('importer') != 'iiif':
            flash('Only IIIF projects can be built from parents.', 'error')
            return

        parent = get_parent(template['parent_template_id'], volume['id'],
                            category)
        if not parent:
            msg = 'There is no valid parent for this template and volume.'
            flash(msg, 'error')
            return

        import_data['parent_id'] = parent.id

    # Create project
    webhook = '{0}lc/analysis'.format(request.url_root)
    project = Project(name=form.name.data,
                      short_name=form.short_name.data,
                      description=template['description'],
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'volume_id': volume['id'],
                          'template_id': template['id']
                      },
                      webhook=webhook,
                      published=True,
                      category_id=category.id,
                      owners_ids=[current_user.id])

    # Add avatar
    if volume.get('container') and volume.get('thumbnail'):
        project.info['container'] = volume['container']
        project.info['thumbnail'] = volume['thumbnail']
        project.info['thumbnail_url'] = volume.get('thumbnail_url')

    project_repo.save(project)

    # Attempt to generate the tasks
    success = True
    try:
        msg = _import_tasks(project, **import_data)
        flash(msg, 'success')
    except BulkImportException as err:   # pragma: no cover
        success = False
        project_repo.delete(project)
        flash(err.message, 'error')

    except Exception as inst:  # pragma: no cover
        success = False
        current_app.logger.error(inst)
        print inst
        project_repo.delete(project)
        msg = 'Uh oh, an error was encountered while generating the tasks'
        flash(msg, 'error')

    if success:
        auditlogger.add_log_entry(None, project, current_user)
        task_repo.update_tasks_redundancy(project, template['min_answers'])
        return redirect_content_type(url_for('home.home'))


def get_parent(parent_template_id, volume_id, category):
    """Return a valid parent project."""
    projects = project_repo.filter_by(category_id=category.id)
    try:
        return [p for p in projects
                if p.info.get('template_id') == parent_template_id and
                p.info.get('volume_id') == volume_id and validate_parent(p)][0]
    except IndexError:
        return None


def validate_parent(project):
    """Validate a parent project."""
    empty_results = [r for r in result_repo.filter_by(project_id=project.id)
                     if not r.info]
    incomplete_tasks = task_repo.filter_tasks_by(state='ongoing',
                                                 project_id=project.id)
    if empty_results or incomplete_tasks:
        return False

    return True


def get_built_projects(category):
    """Get template and volume for all built projects in a category.

    Needed to check which combinations of templates and volumes are still
    available.
    """
    sql = text("""SELECT info->>'template_id' AS template_id,
               info->>'volume_id' AS volume_id
               FROM project
               WHERE category_id = :category_id;
               """)
    session = db.slave_session
    results = session.execute(sql, dict(category_id=category.id))
    return [{'template_id': row.template_id, 'volume_id': row.volume_id}
            for row in results]
