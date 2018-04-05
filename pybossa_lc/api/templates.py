# -*- coding: utf8 -*-
"""API template module for pybossa-lc."""

import json
from rq import Queue
from flask import Blueprint, abort, flash, request, render_template, url_for
from flask import current_app
from flask.ext.login import login_required
from flask_wtf.csrf import generate_csrf
from pybossa.util import handle_content_type, admin_required
from pybossa.util import redirect_content_type
from pybossa.auth import ensure_authorized_to
from pybossa.core import project_repo, user_repo
from pybossa.core import sentinel
from pybossa.jobs import send_mail, enqueue_job
from pybossa.cache import users as users_cache

from ..forms import *
from .. import project_tmpl_repo
from ..model.project_template import ProjectTemplate


BLUEPRINT = Blueprint('lc_templates', __name__)
MAIL_QUEUE = Queue('email', connection=sentinel.master)


def get_changes(form, template, key=None):
    """Get any changes to a template."""
    tmpl_dict = template.to_dict()
    if key:
        return {k: v for k, v in form.data.items()
                if not tmpl_dict.get(key) or tmpl_dict[key].get(k) != v}
    else:
        return {k: v for k, v in form.data.items() if tmpl_dict[k] != v}


def get_template_task_form(task_presenter, method, data):
    """Return the template form for a type of task presenter."""
    if not data:
        data = {}

    if task_presenter == 'iiif-annotation':
        form = IIIFAnnotationTemplateForm(**data)

        # Populate fields schema
        if method == 'POST':
            if data.get('mode') == 'transcribe':
                for field in data.get('fields_schema', []):
                    form.fields_schema.append_entry(field)
            else:
                del form.fields_schema
        return form

    elif task_presenter == 'z3950':
        form = Z3950TemplateForm(**data)
        dbs = current_app.config.get("Z3950_DATABASES", {}).keys()
        form.database.choices = [(k, k.upper()) for k in dbs]

        # Populate institutions
        if method == 'POST':
            for field in data.get('institutions', []):
                form.institutions.append_entry(field)
        return form


@login_required
@BLUEPRINT.route('/<template_id>/update', methods=['GET', 'POST'])
def update_template(template_id):
    """Edit a template's core details."""
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:  # pragma: no cover
        abort(404)

    user = user_repo.get(template.owner_id)
    if not user:  # pragma: no cover
        abort(400)

    ensure_authorized_to('update', user)
    form = ProjectTemplateForm(**template.to_dict())

    # Add category choices
    categories = project_repo.get_all_categories()
    category_choices = [(c.id, c.name) for c in categories]
    form.category_id.choices = category_choices
    if not form.category_id.data:
        form.category_id.data = category_choices[0][0]

    # Add parent template choices
    category_id = int(form.category_id.data)
    templates = project_tmpl_repo.get_by_category_id(category_id)
    parent_tmpl_choices = [(t.id, t.name) for t in templates]
    parent_tmpl_choices.append(('None', ''))
    form.parent_template_id.choices = parent_tmpl_choices

    if request.method == 'POST':
        form = ProjectTemplateForm(request.body)
        form.category_id.choices = category_choices
        form.parent_template_id.choices = parent_tmpl_choices

        if form.validate():
            # Replace 'None' string with None
            if form.parent_template_id.data == 'None':
                form.parent_template_id.data = None

            changes = get_changes(form, template)
            if changes:
                template.update(form.data)
                template.pending = True
                project_tmpl_repo.update_pending(template)
                flash('Updates submitted for approval', 'success')
            else:  # pragma: no cover
                flash('Nothing changed', 'info')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(template=template.to_dict(), form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<template_id>/task', methods=['GET', 'POST'])
def update_template_task(template_id):
    """Update task data for a template."""
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:  # pragma: no cover
        abort(404)

    user = user_repo.get(template.owner_id)
    if not user:  # pragma: no cover
        abort(400)

    ensure_authorized_to('update', user)

    category = project_repo.get_category(template.category_id)
    if not category:
        msg = ('The category for this template no longer exists, please '
               'contact an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('home.home'))

    if not category.info:
        category.info = {}

    # Get the form for the category's task presenter
    presenter = category.info.get('presenter')
    form = get_template_task_form(presenter, request.method, template.task)
    if not form:
        msg = 'This category has an invalid task presenter'
        flash(msg, 'error')
        return redirect_content_type(url_for('home.home'))

    if request.method == 'POST':
        form_data = json.loads(request.data) if request.data else {}
        form = get_template_task_form(presenter, request.method, form_data)

        if form.validate():
            changes = get_changes(form, template, key='task')
            if changes:
                template.task.update(form.data)
                template.pending = True
                project_tmpl_repo.update_pending(template)
                flash('Updates submitted for approval', 'success')
            else:  # pragma: no cover
                flash('Nothing changed', 'info')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    z3950_databases = form.database.choices if presenter == 'z3950' else []
    response = dict(form=form, template=template.to_dict(),
                    presenter=presenter, z3950_databases=z3950_databases)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<template_id>/rules', methods=['GET', 'POST'])
def update_template_rules(template_id):
    """Update resulsts analysis rules for a template."""
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:  # pragma: no cover
        abort(404)

    user = user_repo.get(template.owner_id)
    if not user:  # pragma: no cover
        abort(400)

    ensure_authorized_to('update', user)

    category = project_repo.get_category(template.category_id)
    if not category:
        msg = ('The category for this template no longer exists, please '
               'contact an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('home.home'))

    if not category.info:
        category.info = {}

    current_rules = template.rules or {}
    form = AnalysisRulesForm(**current_rules)

    if request.method == 'POST':
        form = AnalysisRulesForm(request.body)
        if form.validate():
            changes = get_changes(form, template, key='rules')
            if changes:
                template.rules.update(form.data)
                template.pending = True
                project_tmpl_repo.update_pending(template)
                flash('Updates submitted for approval', 'success')
            else:  # pragma: no cover
                flash('Nothing changed', 'info')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(form=form, template=template.to_dict())
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<template_id>/delete', methods=['GET', 'POST'])
def delete(template_id):
    """Delete a pending template."""
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:  # pragma: no cover
        abort(404)

    user = user_repo.get(template.owner_id)
    if not user:  # pragma: no cover
        abort(400)

    ensure_authorized_to('update', user)

    approved = project_tmpl_repo.get(template_id)

    if request.method == 'POST':
        if not approved:
            project_tmpl_repo.delete_pending(template)
            flash('Template deleted', 'success')
        else:
            flash('Approved templates can only be deleted by administrators',
                  'warning')

    response = dict(can_delete=not approved, template=template.to_dict())
    return handle_content_type(response)
