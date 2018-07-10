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
from pybossa.cache.projects import overall_progress
from sqlalchemy import text

from ..forms import *


auditlogger = AuditLogger(auditlog_repo, caller='web')
BLUEPRINT = Blueprint('lc_projects', __name__)


def _import_tasks(project, **import_data):
    """Import the tasks.

    Always runs as a background task to avoid timing out when generating
    parent-child IIIF projects, where even counting the tasks will take a long
    time.
    """
    job = dict(name=import_tasks,
                args=[project.id],
                kwargs=import_data,
                timeout=current_app.config.get('TIMEOUT'),
                queue='medium')
    enqueue_job(job)
    return '''The project's tasks are being generated, you will recieve an
           email when the process is complete.'''


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
    form.volume_id.choices = [(v['id'], v['name']) for v in volumes]
    form.template_id.choices = [(t['id'], t['name']) for t in templates]
    if request.method == 'POST' and form.validate():
        tmpl = [t for t in templates
                if t['id'] == form.template_id.data][0]
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

    add_avatar_to_project_info(project, volume)
    project_repo.save(project)
    return generate_tasks(project, import_data, template)


def add_avatar_to_project_info(project, volume):
    """Add avatar to project info."""
    if volume.get('container') and volume.get('thumbnail'):
        project.info['container'] = volume['container']
        project.info['thumbnail'] = volume['thumbnail']
        project.info['thumbnail_url'] = volume.get('thumbnail_url')


def generate_tasks(project, import_data, template):
    """Generate the tasks."""
    try:
        msg = _import_tasks(project, **import_data)
        flash(msg, 'success')
    except BulkImportException as err:   # pragma: no cover
        project_repo.delete(project)
        flash(err.message, 'error')
        return redirect_content_type(url_for('home.home'))
    except Exception as inst:  # pragma: no cover
        success = False
        current_app.logger.error(inst)
        print inst
        project_repo.delete(project)
        flash(str(inst), 'error')
        return redirect_content_type(url_for('home.home'))

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

    Should refactor some of the above to use this query, which is really the
    core of the additional options for building projects.
    """
    sql = text("""
               WITH empty_results AS (
                   SELECT project.id AS project_id,
                   COUNT(CASE WHEN result.info IS NULL THEN 1 END)
                   FROM project
                   LEFT JOIN result ON project.id = result.project_id
                   GROUP BY project.id
               )
               SELECT project.id,
               project.info->>'template_id' AS template_id,
               project.info->>'volume_id' AS volume_id,
               empty_results.count AS n_empty_results
               FROM project, empty_results, category
               WHERE empty_results.project_id = project.id
               AND category.id = :category_id
               AND category.id = project.category_id
               GROUP BY project.id, project.info, empty_results.count;
               """)
    session = db.slave_session
    results = session.execute(sql, dict(category_id=category.id))
    return [{
        'project_id': row.id,
        'template_id': row.template_id,
        'volume_id': row.volume_id,
        'overall_progress': overall_progress(row.id),
        'empty_results': row.n_empty_results
    } for row in results]
