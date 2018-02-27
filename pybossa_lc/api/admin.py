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
from ..jobs import analyse_all


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

    category = project_repo.get_category(template.category_id)
    if not category:
        abort(400)

    ensure_authorized_to('update', category)

    if request.method == 'POST':
        template.pending = False

        approved_template = project_tmpl_repo.get_approved(template.id)
        if approved_template:
            project_tmpl_repo.update(template, True)
        else:
            project_tmpl_repo.save(template, True)

        # Update user template to remove pending
        project_tmpl_repo.update(template)

        # Reanalyse all results
        presenter = category.info.get('presenter')
        cat_projects = project_repo.filter_by(category_id=category.id)
        tmpl_projects = [project for project in cat_projects
                         if project.info.get('template_id') == template.id]
        for project in tmpl_projects:
            analyse_all(project.id, presenter)

        # Send email
        owner = user_repo.get(template.owner_id)
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

    response = dict(template=template.to_dict(), csrf=csrf)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/templates/<template_id>/reject', methods=['GET', 'POST'])
def reject_template(template_id):
    """Reject updates to a template."""
    template = project_tmpl_repo.get(template_id)
    if not template:
        abort(404)

    if request.method == 'POST':
        template.pending = False
        project_tmpl_repo.update(template)

        # Send email
        owner = user_repo.get(template.owner_id)
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

    response = dict(template=template.to_dict(), csrf=csrf)
    return handle_content_type(response)
