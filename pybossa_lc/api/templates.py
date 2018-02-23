# -*- coding: utf8 -*-
"""API template module for pybossa-lc."""

from flask import Blueprint, abort, flash, request, render_template
from flask.ext.login import login_required
from pybossa.util import handle_content_type, admin_required
from pybossa.auth import ensure_authorized_to
from pybossa.core import project_repo
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

    category = project_repo.get_category(template['id'])
    if not category:
        abort(400)

    owner = templates_cache.get_owner(template_id)
    ensure_authorized_to('update', category)

    if request.method == 'POST':
        approved_templates = category.get('approved_templates', [])
        updated_templates = [tmpl for tmpl in approved_templates
                            if tmpl['id'] != tmpl['id']]
        updated_templates.append(template)
        category.info['approved_templates'] = updated_templates

        project_repo.update_category(category)

        recipients = [owner['id']]
        msg = dict(subject='Template Updates Accepted', recipients=recipients)
        msg['body'] = render_template('/lc/email/template_accepted.md',
                                      owner=owner, reason=reason)
        msg['html'] = render_template('/lc/email/template_accepted.html',
                                      owner=owner, reason=reason)
        enqueue_job(send_mail, msg)
        flash('Template updated', 'success')

    response = dict(template=tmpl)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/<template_id>/reject', methods=['GET', 'POST'])
def reject(template_id):
    """Reject template updates."""
    template = templates_cache.get_by_id(template_id)
    if not template:
        abort(404)

    owner = templates_cache.get_owner(template_id)
    recipients = [owner['id']]
    reason = request.args.get('reason')
    msg = dict(subject='Template Updates Rejected', recipients=recipients)
    msg['body'] = render_template('/lc/email/template_rejected.md',
                                  owner=owner, reason=reason)
    msg['html'] = render_template('/lc/email/template_rejected.html',
                                  owner=owner, reason=reason)
    enqueue_job(send_mail, msg)

    flash('Email sent to template owner', 'success')
    response = dict()
    return handle_content_type(response)
