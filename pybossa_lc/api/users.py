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

from ..forms import *
from ..cache import templates as templates_cache

BLUEPRINT = Blueprint('users', __name__)


def get_template_form(task_presenter, method, data):
    """Return the template form for a type of task presenter."""
    if not data:
        data = {}

    if task_presenter == 'iiif-annotation':
        form = IIIFAnnotationTemplateForm(**data)

        # Populate fields schema for IIIF Transcribe tasks only
        if data.get('mode') == 'transcribe':
            form.fields_schema.pop_entry()
            for field in data.get('fields_schema', []):
                form.fields_schema.append_entry(field)
        elif method == 'POST':
            del form.fields_schema
        return form

    elif task_presenter == 'z3950':
        form = Z3950TemplateForm(**data)
        dbs = current_app.config.get("Z3950_DATABASES", {}).keys()
        form.database.choices = [(k, k.upper()) for k in dbs]

        # Populate institutions
        form.institutions.pop_entry()
        for field in data.get('institutions', []):
            form.institutions.append_entry(field)
        return form


@login_required
@BLUEPRINT.route('/<name>/templates', methods=['GET', 'POST'])
def templates(name):
    """List or add to a user's templates."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    user_templates = user.info.get('templates', [])

    categories = project_repo.get_all_categories()
    form = ProjectTemplateForm(request.body)
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if request.method == 'POST' and form.validate():
        tmpl_id = str(uuid.uuid4())
        new_template = dict(id=tmpl_id, project=form.data, task=None,
                            rules=None)
        user_templates.append(new_template)
        user.info['templates'] = user_templates
        user_repo.update(user)
        templates_cache.reset()
        flash("Project template created", 'success')
        return redirect_content_type(url_for('.template',
                                             name=user.name, tmpl_id=tmpl_id))
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    response = dict(templates=user_templates, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>', methods=['GET', 'POST'])
def template(name, tmpl_id):
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
    form = ProjectTemplateForm(data=tmpl['project'])
    form.category_id.choices = category_choices

    if request.method == 'POST':
        form = ProjectTemplateForm(request.body)
        form.category_id.choices = category_choices

        if form.validate():
            try:
                idx = [i for i, _t in enumerate(user_templates)
                       if _t['id'] == tmpl_id][0]
            except IndexError:  # pragma: no cover
                abort(404)
            tmpl['project'] = form.data
            user_templates[idx] = tmpl
            user.info['templates'] = user_templates
            user_repo.update(user)
            templates_cache.reset()
            flash("Project template updated", 'success')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(template=tmpl)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>/tasks', methods=['GET', 'POST'])
def template_task(name, tmpl_id):
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

    category = project_repo.get_category(tmpl['project']['category_id'])
    if not category:
        msg = ('The category for this template no longer exists, please '
               'contact an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    # Get the form for the category's task presenter
    presenter = category.info.get('presenter')
    form = get_template_form(presenter, request.method, tmpl['task'])
    if not form:
        msg = 'This category has an invalid task presenter'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if request.method == 'POST':
        form_data = json.loads(request.data) if request.data else {}
        form = get_template_form(presenter, request.method, form_data)

        if form.validate():
            try:
                idx = [i for i, _t in enumerate(user_templates)
                       if _t['id'] == tmpl_id][0]
            except IndexError:
                abort(404)

            tmpl['task'] = form.data
            user_templates[idx] = tmpl
            user.info['templates'] = user_templates
            user_repo.update(user)
            flash("Task template updated", 'success')
        else:
            flash('Please correct the errors', 'error')
    response = dict(form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>/rules',
                 methods=['GET', 'POST'])
def template_rules(name, tmpl_id):
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

    category = project_repo.get_category(tmpl['project']['category_id'])
    if not category:
        msg = 'The category for this template no longer exists'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    presenter = category.info.get('presenter')
    if presenter != 'iiif-annotation':
        msg = 'No normalisation rules available for this presenter type'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if not tmpl['task'] or tmpl['task'].get('mode') != 'transcribe':
        msg = 'Analysis rules only available for IIIF transcription projects'
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    form = NormalisationRulesForm(data=tmpl['rules'] or {})

    if request.method == 'POST':
        form = NormalisationRulesForm(request.body)
        if form.validate():
            try:
                idx = [i for i, _t in enumerate(user_templates)
                       if _t['id'] == tmpl_id][0]
            except IndexError:  # pragma: no cover
                abort(404)
            tmpl['rules'] = form.data
            user_templates[idx] = tmpl
            user.info['templates'] = user_templates
            user_repo.update(user)
            templates_cache.reset()
            flash("Results analysis rules updated", 'success')
        else:  # pragma: no cover
            flash('Please correct the errors', 'error')

    response = dict(template=tmpl)
    return handle_content_type(response)
