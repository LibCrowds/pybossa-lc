# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

import json
from flask import Response, Blueprint, flash, request, abort, url_for
from flask import current_app
from flask.ext.login import login_required, current_user
from pybossa.util import handle_content_type
from pybossa.util import redirect_content_type
from pybossa.core import user_repo
from pybossa.auth import ensure_authorized_to

from ..forms import *
from ..model.project_template import ProjectTemplate
from .. import project_tmpl_repo


BLUEPRINT = Blueprint('users', __name__)


@login_required
@BLUEPRINT.route('/<name>/templates', methods=['GET', 'POST'])
def templates(name):
    """List or add to a user's templates."""
    user = user_repo.get_by_name(name)
    if not user:  # pragma: no cover
        abort(404)

    ensure_authorized_to('update', user)
    templates = project_tmpl_repo.get_by_owner_id(user.id)

    # Use a default category so we can create the form
    categories = project_repo.get_all_categories()
    data = request.body.to_dict(flat=False)
    if not data.get('category_id'):
        data['category_id'] = categories[0].id

    form = ProjectTemplateForm(**data)
    category_choices = [(c.id, c.name) for c in categories]
    form.category_id.choices = category_choices

    if request.method == 'POST' and form.validate():
        new_template = ProjectTemplate(
            name=form.name.data,
            description=form.description.data,
            owner_id=user.id,
            category_id=form.category_id.data,
            min_answers=form.min_answers.data,
            max_answers=form.max_answers.data,
            tutorial=form.tutorial.data
        )
        project_tmpl_repo.save(new_template)
        flash("New template submitted for approval", 'success')
        return redirect_content_type(url_for('lc_templates.update_template',
                                             template_id=new_template.id))
    elif request.method == 'POST':  # pragma: no cover
        flash('Please correct the errors', 'error')

    tmpl_dicts = [tmpl.to_dict() for tmpl in templates]
    response = dict(templates=tmpl_dicts, form=form)
    return handle_content_type(response)
