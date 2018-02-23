# -*- coding: utf8 -*-
"""API template module for pybossa-lc."""

from flask import Blueprint, abort, flash, request, render_template
from flask.ext.login import login_required
from flask_wtf.csrf import generate_csrf
from pybossa.util import handle_content_type, admin_required
from pybossa.auth import ensure_authorized_to
from pybossa.core import project_repo, user_repo
from pybossa.jobs import send_mail, enqueue_job

from ..cache import templates as templates_cache


BLUEPRINT = Blueprint('templates', __name__)


@login_required
@BLUEPRINT.route('/')
def get_templates():
    """Return all templates."""
    templates = templates_cache.get_approved()
    response = dict(templates=templates)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/pending')
def pending():
    """Return all templates."""
    templates = templates_cache.get_pending()
    response = dict(templates=templates)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/<template_id>/approve', methods=['GET', 'POST'])
def approve(template_id):
    """Approve template updates."""
    template = templates_cache.get_by_id(template_id)
    if not template:
        abort(404)

    category_id = int(template['category_id'])
    category = project_repo.get_category(category_id)
    if not category:
        abort(400)

    ensure_authorized_to('update', category)

    if request.method == 'POST':
        template['pending'] = False

        # Update category approved template
        approved_templates = category.info.get('approved_templates', [])
        updated_templates = [tmpl for tmpl in approved_templates
                             if tmpl['id'] != template['id']]
        updated_templates.append(template)
        category.info['approved_templates'] = updated_templates
        project_repo.update_category(category)

        # Update owner's template
        owner_id = int(template['owner_id'])
        owner = user_repo.get(owner_id)
        owner_templates = [tmpl for tmpl in owner.info.get('templates', [])
                           if tmpl['id'] != template['id']]
        updated_templates.append(template)
        owner.info['templates'] = owner_templates
        user_repo.update(owner)

        # Send email
        msg = dict(subject='Template Updates Accepted', recipients=[owner.id])
        msg['body'] = render_template('/lc/email/template_accepted.md',
                                      owner=owner)
        msg['html'] = render_template('/lc/email/template_accepted.html',
                                      owner=owner)
        enqueue_job(send_mail, msg)
        flash('Template updated', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(template=template, csrf=csrf)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/<template_id>/reject', methods=['GET', 'POST'])
def reject(template_id):
    """Reject template updates."""
    template = templates_cache.get_by_id(template_id)
    if not template:
        abort(404)

    if request.method == 'POST':
        owner_id = int(template['owner_id'])
        owner = user_repo.get(owner_id)
        reason = request.args.get('reason')
        msg = dict(subject='Template Updates Rejected', recipients=[owner.id])
        msg['body'] = render_template('/lc/email/template_rejected.md',
                                    owner=owner, reason=reason)
        msg['html'] = render_template('/lc/email/template_rejected.html',
                                    owner=owner, reason=reason)
        enqueue_job(send_mail, msg)
        flash('Email sent to template owner', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(template=template, csrf=csrf)
    return handle_content_type(response)
