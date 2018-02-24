# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import uuid
import json
from flask import Response, Blueprint, flash, request, abort, jsonify, url_for
from flask import current_app
from flask.ext.login import login_required, current_user
from pybossa.util import admin_required, handle_content_type
from pybossa.util import redirect_content_type
from pybossa.core import project_repo, user_repo
from pybossa.auth import ensure_authorized_to
from pybossa.cache import users as users_cache

from ..forms import *
from ..cache import templates as templates_cache

BLUEPRINT = Blueprint('users', __name__)


def get_task_template_form(task_presenter, method, data):
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


def propose_template_update(form, user, template_id, key=None):
    user_templates = user.info.get('templates', [])
    try:
        idx = [i for i, tmpl in enumerate(user_templates)
                if tmpl['id'] == template_id][0]
    except IndexError:  # pragma: no cover
        abort(404)

    tmpl = user_templates[idx]
    if key:
        changes = {k: v for k, v in form.data.items()
                   if not tmpl[key] or tmpl[key][k] != v}
    else:
        changes = {k: v for k, v in form.data.items() if tmpl[k] != v}

    if changes:
        tmpl['pending'] = True
        current_changes = tmpl.get('changes', {})
        if key:
            current_changes[key] = form.data
        else:
            current_changes.update(form.data)
        tmpl['changes'] = current_changes
        user_templates[idx] = tmpl
        user.info['templates'] = user_templates
        user_repo.update(user)
        templates_cache.reset()
        users_cache.delete_user_summary_id(user.id)


@login_required
@BLUEPRINT.route('/<name>/templates', methods=['GET', 'POST'])
def templates(name):
    """List or add to a user's templates."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    if current_user.admin:
        templates = templates_cache.get_all()
    else:
        templates = user.info.get('templates', [])

    # Use a default category so we can create the form
    categories = project_repo.get_all_categories()
    data = request.body.to_dict(flat=False)
    if not data.get('category_id'):
        data['category_id'] = categories[0].id

    form = ProjectTemplateForm(**data)
    category_choices = [(c.id, c.name) for c in categories]
    form.category_id.choices = category_choices

    if request.method == 'POST' and form.validate():
        tmpl_id = str(uuid.uuid4())
        new_template = form.data
        new_template.update({
            'id': tmpl_id,
            'owner_id': user.id,
            'pending': True,
            'task': None,
            'rules': None
        })
        templates.append(new_template)
        user.info['templates'] = templates
        user_repo.update(user)
        templates_cache.reset()
        users_cache.delete_user_summary_id(user.id)
        flash("New template submitted for approval", 'success')
        return redirect_content_type(url_for('.update_template_core',
                                             name=user.name, tmpl_id=tmpl_id))
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(templates=templates, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>', methods=['GET', 'POST'])
def update_template_core(name, tmpl_id):
    """View or edit the main template project data."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    user_templates = user.info.get('templates', [])
    user_tmpl_ids = [t['id'] for t in user_templates]
    tmpl = templates_cache.get_by_id(tmpl_id)
    if not tmpl:
        abort(404)
    elif tmpl['id'] not in user_tmpl_ids:
        abort(403)

    categories = project_repo.get_all_categories()
    category_choices = [(c.id, c.name) for c in categories]
    form = ProjectTemplateForm(**tmpl)
    form.category_id.choices = category_choices
    if not form.category_id.data:
        form.category_id.data = category_choices[0][0]

    if request.method == 'POST':
        form = ProjectTemplateForm(request.body)
        form.category_id.choices = category_choices

        if form.validate():
            propose_template_update(form, user, tmpl_id)
            flash("Template updates submitted for approval", 'success')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(template=tmpl, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>/task', methods=['GET', 'POST'])
def update_task_template(name, tmpl_id):
    """Add task data for a template."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    user_templates = user.info.get('templates', [])
    user_tmpl_ids = [t['id'] for t in user_templates]
    tmpl = templates_cache.get_by_id(tmpl_id)
    if not tmpl:
        abort(404)
    elif tmpl['id'] not in user_tmpl_ids:
        abort(403)

    category = project_repo.get_category(tmpl['category_id'])
    if not category:
        msg = ('The category for this template no longer exists, please '
               'contact an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if not category.info:
        category.info = {}

    # Get the form for the category's task presenter
    presenter = category.info.get('presenter')
    form = get_task_template_form(presenter, request.method, tmpl['task'])
    if not form:
        msg = 'This category has an invalid task presenter'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if request.method == 'POST':
        form_data = json.loads(request.data) if request.data else {}
        form = get_task_template_form(presenter, request.method, form_data)

        if form.validate():
            propose_template_update(form, user, tmpl_id, key='task')
            flash("Template updates submitted for approval", 'success')
        else:
            flash('Please correct the errors', 'error')

    z3950_databases = form.database.choices if presenter == 'z3950' else []
    response = dict(form=form, template=tmpl, presenter=presenter,
                    z3950_databases=z3950_databases)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>/rules',
                 methods=['GET', 'POST'])
def update_template_rules(name, tmpl_id):
    """Add resulsts analysis rules for a template."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    user_templates = user.info.get('templates', [])
    user_tmpl_ids = [t['id'] for t in user_templates]
    tmpl = templates_cache.get_by_id(tmpl_id)
    if not tmpl:
        abort(404)
    elif tmpl['id'] not in user_tmpl_ids:
        abort(403)

    category = project_repo.get_category(tmpl['category_id'])
    if not category:
        msg = 'The category for this template no longer exists'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if not category.info:
        category.info = {}

    presenter = category.info.get('presenter')
    current_rules = tmpl['rules'] or {}
    form = AnalysisRulesForm(**current_rules)

    if request.method == 'POST':
        form = AnalysisRulesForm(request.body)
        if form.validate():
            propose_template_update(form, user, tmpl_id, key='rules')
            flash("Template updates submitted for approval", 'success')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(form=form, template=tmpl, presenter=presenter)
    return handle_content_type(response)
