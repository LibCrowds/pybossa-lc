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
from ..cache import results as results_cache
from ..jobs import analyse_all


BLUEPRINT = Blueprint('lc_admin', __name__)
MAIL_QUEUE = Queue('email', connection=sentinel.master)


@login_required
@admin_required
@BLUEPRINT.route('/templates/pending')
def pending_templates():
    """Return pending templates, enhanced with diffs."""
    pending_templates = project_tmpl_repo.get_all_pending()
    approved_templates = project_tmpl_repo.get_all()
    approved_tmpls_idx = {tmpl.id: tmpl for tmpl in approved_templates}
    enhanced_templates = []
    for pending_tmpl in pending_templates:
        tmpl_dict = pending_tmpl.to_dict()
        tmpl_dict['_original'] = None
        approved_tmpl = approved_tmpls_idx.get(pending_tmpl.id)
        if approved_tmpl:
            tmpl_dict['_original'] = approved_tmpl.to_dict()
        enhanced_templates.append(tmpl_dict)

    response = dict(templates=enhanced_templates)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/templates/<template_id>/approve', methods=['GET', 'POST'])
def approve_template(template_id):
    """Approve updates to a template."""
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:
        abort(404)

    category = project_repo.get_category(template.category_id)
    if not category:
        abort(400)

    ensure_authorized_to('update', category)

    if request.method == 'POST':
        template.pending = False
        project_tmpl_repo.approve(template)

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
    template = project_tmpl_repo.get_user_template(template_id)
    if not template:
        abort(404)

    if request.method == 'POST':
        template.pending = False
        project_tmpl_repo.update_pending(template)

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


@login_required
@admin_required
@BLUEPRINT.route('/results')
def results():
    """Return an overview of results for each category."""
    unanalysed_categories = results_cache.get_unanalysed_by_category()

    if request.method == 'POST':
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(unanalysed_categories=unanalysed_categories)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/results/analyse/all/<int:category_id>')
def analyse_all_results(category_id):
    """Analyse all results for a category."""
    category = project_repo.get_category(category_id)
    if not category:
        abort(404)

    if request.method == 'POST':
        presenter = category.info.get('presenter')
        projects = project_repo.filter_by(category_id=category.id)
        for project in projects:
            analyse_all(project.id, presenter)
        flash('Analysis of all results queued', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(csrf=csrf)
    return handle_content_type(response)


@login_required
@admin_required
@BLUEPRINT.route('/results/analyse/empty/<int:category_id>')
def analyse_empty_results(category_id):
    """Analyse empty results for a category."""
    category = project_repo.get_category(category_id)
    if not category:
        abort(404)

    if request.method == 'POST':
        presenter = category.info.get('presenter')
        projects = project_repo.filter_by(category_id=category.id)
        for project in projects:
            analyse_empty(project.id, presenter)
        flash('Analysis of empty results queued', 'success')
        csrf = None
    else:
        csrf = generate_csrf()

    response = dict(csrf=csrf)
    return handle_content_type(response)
