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

from ..cache.users import get_user_templates
from ..forms import *


BLUEPRINT = Blueprint('users', __name__)


def get_template_form(task_presenter, method, data):
    """Return the template form for a type of task presenter."""
    if task_presenter == 'iiif-annotation':
        form = IIIFAnnotationTemplateForm(**data)
        if data['mode'] == 'transcribe':

            # Populate fields schema
            form.fields_schema.pop_entry()
            for field in data.get('fields_schema', []):
                form.fields_schema.append_entry(field)

        elif method == 'POST':
            del form.fields_schema

        # Populate coowners
        for field in data.get('coowners', []):
            form.coowners.append_entry(field)

        return form

    elif task_presenter == 'z3950':
        form = Z3950TemplateForm(**data)
        dbs = current_app.config.get("Z3950_DATABASES", {}).keys()
        form.database.choices = [(k, k.upper()) for k in dbs]

        # Populate institutions
        form.institutions.pop_entry()
        for field in data.get('institutions', []):
            form.institutions.append_entry(field)

        # Populate coowners
        for field in data.get('coowners', []):
            form.coowners.append_entry(field)

        return form


@login_required
@admin_required
@BLUEPRINT.route('/<name>/templates',
                 methods=['GET', 'POST'])
def templates(name):
    """List a user's templates."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no-cover
        abort(404)
    ensure_authorized_to('update', user)
    user_templates = get_user_templates(user.id)
    response = dict(templates=user_templates)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/<name>/templates/add/<cat_short_name>',
                 methods=['GET', 'POST'])
def category_templates(name, cat_short_name):
    """Add a template for a category."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no-cover
        abort(404)

    category = project_repo.get_category_by(short_name=cat_short_name)
    if not category:  # pragma: no-cover
        abort(404)

    ensure_authorized_to('update', user)

    task_presenter = category.info.get('presenter')
    form_data = json.loads(request.data) if request.data else {}
    form = get_template_form(task_presenter, request.method, form_data)
    if not form:
        msg = ('This category has an invalid task presenter, please contact '
               'an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    del form.id
    if request.method == 'POST' and form.validate():
        new_template = form.data
        new_template['id'] = str(uuid.uuid4())
        new_template['category_id'] = category.id
        user_templates = user.info.get('templates', [])
        user_templates.append(new_template)
        user.info['templates'] = user_templates
        user_repo.update(user)
        flash("Project template created", 'success')
    else:
        print form.errors
        flash('Please correct the errors', 'error')
    response = dict(form=form)
    return handle_content_type(response)

@login_required
@admin_required
@BLUEPRINT.route('/<int:category_id>/templates/<int:template_id>',
                 methods=['GET', 'POST'])
def update_template(category_id, template_id):
    """Update a project template."""
    category = project_repo.get_category(category_id)
    if not category:  # pragma: no-cover
        abort(jsonify(message="Category not found"), 404)

    ensure_authorized_to('update', category)

    try:
        template = [t for t in category.info.get('templates', [])
                    if t['id'] == template_id][0]
    except IndexError:
        abort(jsonify(message="Template not found"), 404)

    task_presenter = category.info.get('presenter')
    form = get_template_form(task_presenter, request.method, request.body)
    if not form:
        flash('Invalid task presenter', 'error')
        return redirect_content_type(url_for('admin.categories'))

    if request.method == 'POST' and form.validate():
        category_templates = category.info.get('templates', [])
        for idx, tmpl in enumerate(category_templates):
            if tmpl['id'] == form.id.data:
                category_templates[idx] = form.data

        category.info['templates'] = category_templates
        project_repo.update_category(category)
        cached_cat.reset()
        flash("Project template updated", 'success')
    else:
        flash('Please correct the errors', 'error')
    response = dict(form=form)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/<int:category_id>/templates/<int:template_id>/delete',
                 methods=['POST'])
def delete_template(category_id, template_id):
    """Delete a project template."""
    category = project_repo.get_category(category_id)
    if not category:  # pragma: no-cover
        abort(jsonify(message="Category not found"), 404)

    ensure_authorized_to('update', category)

    try:
        template = [t for t in category.info.get('templates', [])
                    if t['id'] == template_id][0]
    except KeyError:
        abort(jsonify(message="Template not found"), 404)

    if request.method == 'POST':
        category_templates = [t for t in category.info.get('templates', [])
                              if t['id'] != template_id]
        category.info['templates'] = category_templates
        project_repo.update_category(category)
        cached_cat.reset()
        flash("Project template deleted", 'success')
    else:
        flash('Please correct the errors', 'error')
    return handle_content_type({})
