# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import uuid
import json
from flask import Response, Blueprint, flash, request, abort, jsonify
from flask.ext.login import login_required, current_user
from pybossa.util import admin_required, handle_content_type
from pybossa.cache import categories as cached_cat
from pybossa.core import project_repo
from pybossa.auth import ensure_authorized_to

from ..forms import ProjectTemplateForm

BLUEPRINT = Blueprint('categories', __name__)


@login_required
@admin_required
@BLUEPRINT.route('/<int:category_id>/templates', methods=['GET', 'POST'])
def templates(category_id):
    """Add a project template."""
    category = project_repo.get_category(category_id)
    if not category:  # pragma: no-cover
        abort(jsonify(message="Category not found"), 404)

    ensure_authorized_to('update', category)

    form = ProjectTemplateForm(request.body)

    if request.method == 'POST' and form.validate():
        template = {
            'id': str(uuid.uuid4()),
            'name': form.name.data,
            'tag': form.tag.data,
            'description': form.description.data,
            'objective': form.objective.data,
            'guidance': form.guidance.data,
            'tutorial': form.tutorial.data,
            'mode': form.mode.data
        }
        category_templates = category.info.get('templates', [])
        category_templates.append(template)
        category.info['templates'] = category_templates
        project_repo.update_category(category)
        cached_cat.reset()
        flash("Project template created", 'success')
    else:
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

    print category.info.get('templates', [])

    try:
        template = [t for t in category.info.get('templates', [])
                    if t['id'] == template_id][0]
    except IndexError:
        abort(jsonify(message="Template not found"), 404)

    form = ProjectTemplateForm(**template)

    if request.method == 'POST' and form.validate():
        form = ProjectTemplateForm(request.body)
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
