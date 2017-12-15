# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""
import uuid
from flask import Response, Blueprint, flash, request, abort
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
    if not category:
        abort(404)

    if request.method == 'GET':
        ensure_authorized_to('read', category)
        form = ProjectTemplateForm()

    if request.method == 'POST' and form.validate():
        ensure_authorized_to('update', category)
        form = ProjectTemplateForm(request.body)
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
        flash("Project template added", 'success')
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
    if not category:
        abort(404)

    templates = [template for template in category.info.get('templates', [])
                 if template['id'] == template_id]
    if not templates:
        abort(404)

    if len(templates) > 1:
        err = ValueError('')
        current_app.logger.error(e)
        abort(500)

    template = templates[0]

    if request.method == 'GET':
        ensure_authorized_to('read', category)
        form = ProjectTemplateForm()

    if request.method == 'POST' and form.validate():
        ensure_authorized_to('update', category)
        form = ProjectTemplateForm(request.body)
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
        flash("Project template added", 'success')
    else:
        flash('Please correct the errors', 'error')
    response = dict(form=form)
    return handle_content_type(response)
