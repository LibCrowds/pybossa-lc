# -*- coding: utf8 -*-
"""API admin module for pybossa-lc."""

from rq import Queue
from flask import Blueprint, abort, flash, request, render_template
from flask.ext.login import login_required
from flask_wtf.csrf import generate_csrf
from pybossa.util import handle_content_type, admin_required
from pybossa.auth import ensure_authorized_to
from pybossa.core import project_repo, user_repo
from pybossa.core import sentinel
from pybossa.jobs import send_mail, enqueue_job

from .. import project_tmpl_repo


BLUEPRINT = Blueprint('lc_admin', __name__)
MAIL_QUEUE = Queue('email', connection=sentinel.master)


@login_required
@admin_required
@BLUEPRINT.route('/templates/pending')
def pending_templates():
    """Return pending templates."""
    templates = project_tmpl_repo.get_all()
    tmpl_dicts = [tmpl.to_dict() for tmpl in templates]
    response = dict(templates=tmpl_dicts)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/templates/<template_id>/approve', methods=['GET', 'POST'])
def approve_template(template_id):
    """Approve updates to a template."""
    template = project_tmpl_repo.get(template_id)
    if not template:
        abort(404)

    category_id = int(template['category_id'])
    category = project_repo.get_category(category_id)
    if not category:
        abort(400)

    ensure_authorized_to('update', category)

    if request.method == 'POST':
        changes = template.pop('changes', {})
        template.update(changes)
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
        owner_templates.append(template)
        owner.info['templates'] = owner_templates
        user_repo.update(owner)

        templates_cache.reset()

        # Send email
        msg = dict(subject='Template Updates Accepted', recipients=[owner.id])
        msg['body'] = render_template('/account/email/template_accepted.md',
                                      user=owner, template=template)
        msg['html'] = render_template('/account/email/template_accepted.html',
                                      user=owner, template=template)
        MAIL_QUEUE.enqueue(send_mail, msg)
        flash('Template approved', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(template=template, csrf=csrf)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/templates/<template_id>/reject', methods=['GET', 'POST'])
def reject_template(template_id):
    """Reject updates to a template."""
    template = templates_cache.get_by_id(template_id)
    if not template:
        abort(404)

    if request.method == 'POST':
        # Remove pending from user's template
        template['pending'] = False
        owner_id = int(template['owner_id'])
        owner = user_repo.get(owner_id)
        owner_templates = [tmpl for tmpl in owner.info.get('templates', [])
                           if tmpl['id'] != template['id']]
        owner_templates.append(template)
        owner.info['templates'] = owner_templates
        user_repo.update(owner)

        templates_cache.reset()

        # Send email
        reason = request.json.get('reason')
        msg = dict(subject='Template Updates Rejected', recipients=[owner.id])
        msg['body'] = render_template('/account/email/template_rejected.md',
                                      user=owner, reason=reason,
                                      template=template)
        msg['html'] = render_template('/account/email/template_rejected.html',
                                      user=owner, reason=reason,
                                      template=template)
        MAIL_QUEUE.enqueue(send_mail, msg)
        flash('Email sent to template owner', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(template=template, csrf=csrf)
    return handle_content_type(response)