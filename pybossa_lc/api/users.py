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

from ..cache import templates as templates_cache
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
@BLUEPRINT.route('/<name>/templates', methods=['GET', 'POST'])
def templates(name):
    """List or add to a user's templates."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no-cover
        abort(404)

    ensure_authorized_to('update', user)
    user_templates = templates_cache.get_all(user.id)
    form = ProjectTemplateForm(request.body)
    categories = project_repo.get_all_categories()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if request.method == 'POST' and form.validate():
        tmpl_id = str(uuid.uuid4())
        new_template = dict(id=tmpl_id, project=form.data, task=None)
        user_templates = user.info.get('templates', [])
        user_templates.append(new_template)
        user.info['templates'] = user_templates
        user_repo.update(user)
        templates_cache.reset(user.id)
        flash("Project template created", 'success')
        return redirect_content_type(url_for('.update_template',
                                             name=user.name, tmpl_id=tmpl_id))
    elif request.method == 'POST':
        flash('Please correct the errors', 'error')

    response = dict(templates=user_templates, form=form)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>', methods=['GET'])
def update_template(name, tmpl_id):
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no-cover
        abort(404)

    # Get template if user is owner or coowner
    tmpl = templates_cache.get_by_id(user.id, tmpl_id)
    if not tmpl:
        abort(404)

    response = dict(template=tmpl)
    return handle_content_type(response)


@login_required
@BLUEPRINT.route('/<name>/templates/<tmpl_id>/tasks',
                 methods=['GET', 'POST'])
def template_task(name, tmpl_id):
    """Add task data for a template."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no-cover
        abort(404)

    tmpl = templates_cache.get_by_id(user.id, tmpl_id)
    if not tmpl:
        abort(404)

    category = project_repo.get_category(tmpl['project']['category_id'])
    if not category:
        msg = ('The category for this template no longer exists, please '
               'contact an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    # Get the form for the category's task presenter
    task_presenter = category.info.get('presenter')
    form_data = json.loads(request.data) if request.data else {}
    form = get_template_form(task_presenter, request.method, form_data)
    if not form:
        msg = ('This category has an invalid task presenter, please contact '
               'an administrator')
        flash(msg, 'error')
        return redirect_content_type(url_for('.templates', name=user.name))

    if request.method == 'POST' and form.validate():
        user_templates = user.info.get('templates', [])
        try:
            idx = [i for i, _item in enumerate(user_templates)
                   if user_templates[i]['id'] == tmpl['id']][0]
        except IndexError:
            abort(404)

        tmpl['task'] = form.data
        user_templates[idx] = tmpl
        user.info['templates'] = user_templates
        user_repo.update(user)
        templates_cache.reset(user.id)
        flash("Task template updated", 'success')
    elif request.method == 'POST':
        flash('Please correct the errors', 'error')
    response = dict(form=form)
    return handle_content_type(response)

# @login_required
# @admin_required
# @BLUEPRINT.route('/<int:category_id>/templates/<int:template_id>',
#                  methods=['GET', 'POST'])
# def update_template(category_id, template_id):
#     """Update a project template."""
#     category = project_repo.get_category(category_id)
#     if not category:  # pragma: no-cover
#         abort(jsonify(message="Category not found"), 404)

#     ensure_authorized_to('update', category)

#     try:
#         template = [t for t in category.info.get('templates', [])
#                     if t['id'] == template_id][0]
#     except IndexError:
#         abort(jsonify(message="Template not found"), 404)

#     task_presenter = category.info.get('presenter')
#     form = get_template_form(task_presenter, request.method, request.body)
#     if not form:
#         flash('Invalid task presenter', 'error')
#         return redirect_content_type(url_for('admin.categories'))

#     if request.method == 'POST' and form.validate():
#         category_templates = category.info.get('templates', [])
#         for idx, tmpl in enumerate(category_templates):
#             if tmpl['id'] == form.id.data:
#                 category_templates[idx] = form.data

#         category.info['templates'] = category_templates
#         project_repo.update_category(category)
#         cached_cat.reset()
#         flash("Project template updated", 'success')
#     else:
#         flash('Please correct the errors', 'error')
#     response = dict(form=form)
#     return handle_content_type(response)


# @login_required
# @admin_required
# @BLUEPRINT.route('/<int:category_id>/templates/<int:template_id>/delete',
#                  methods=['POST'])
# def delete_template(category_id, template_id):
#     """Delete a project template."""
#     category = project_repo.get_category(category_id)
#     if not category:  # pragma: no-cover
#         abort(jsonify(message="Category not found"), 404)

#     ensure_authorized_to('update', category)

#     try:
#         template = [t for t in category.info.get('templates', [])
#                     if t['id'] == template_id][0]
#     except KeyError:
#         abort(jsonify(message="Template not found"), 404)

#     if request.method == 'POST':
#         category_templates = [t for t in category.info.get('templates', [])
#                               if t['id'] != template_id]
#         category.info['templates'] = category_templates
#         project_repo.update_category(category)
#         cached_cat.reset()
#         flash("Project template deleted", 'success')
#     else:
#         flash('Please correct the errors', 'error')
#     return handle_content_type({})
