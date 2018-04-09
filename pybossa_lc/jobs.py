# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

from flask import current_app
from pybossa.core import project_repo, announcement_repo
from pybossa.core import sentinel
from pybossa.model.announcement import Announcement
from pybossa.jobs import schedule_job, enqueue_job, send_mail
from rq_scheduler import Scheduler

from . import project_tmpl_repo, analyst

MINUTE = 60
HOUR = 60 * MINUTE


def enqueue_periodic_jobs():
    """Queue periodic tasks."""
    redis_conn = sentinel.master
    scheduler = Scheduler(queue_name='scheduled_jobs', connection=redis_conn)
    jobs_names = [
        check_for_invalid_templates,
        check_for_invalid_volumes
    ]
    for name in jobs_names:
        schedule_job({
            'name': name,
            'args': [],
            'interval': 1 * HOUR,
            'kwargs': {},
            'timeout': 30 * MINUTE
        }, scheduler)


def check_for_invalid_templates():
    """Warn administrators if any projects have missing templates."""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    for category in categories:
        if not category.info.get('published'):
            continue

        templates = project_tmpl_repo.get_by_category_id(category.id)
        valid_tmpl_ids = [tmpl.id for tmpl in templates]
        projects = project_repo.filter_by(category_id=category.id)
        for project in projects:
            project_tmpl_id = project.info.get('template_id')
            if not project_tmpl_id or project_tmpl_id not in valid_tmpl_ids:
                send_project_warning(project, 'Invalid Template')


def check_for_invalid_volumes():
    """Warn administrators if any projects have missing volumes."""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    for category in categories:
        if not category.info.get('published'):
            continue

        valid_vol_ids = [vol['id'] for vol in category.info.get('volumes', [])]
        projects = project_repo.filter_by(category_id=category.id)
        for project in projects:
            project_vol_id = project.info.get('volume_id')
            if not project_vol_id or project_vol_id not in valid_vol_ids:
                send_project_warning(project, 'Invalid Volume')


def send_project_warning(project, subject):
    """Send a warning about a project to administrators."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    url_base = '{}/api/project'.format(spa_server_name)
    subject = "PROJECT {0}: {1}".format(project.id, subject)
    body = "Please review the following project:"
    body += "\n\n"
    body += project.name
    body += "\n\n"
    body += "{0}/{1}".format(url_base, project.id)
    mail_dict = dict(recipients=current_app.config.get('ADMINS'),
                     subject=subject, body=body)
    send_mail(mail_dict)


def analyse_all(project_id, presenter):
    """Queue analysis of all results for a project."""
    timeout = 1 * HOUR
    if analyst:
        job = dict(name=analyst.analyse_all,
                   args=[],
                   kwargs={
                       'presenter': presenter,
                       'project_id': project_id
                   },
                   timeout=timeout,
                   queue='high')
        enqueue_job(job)


def analyse_empty(project_id, presenter):
    """Queue analysis of all empty results for a proejct."""
    timeout = 1 * HOUR
    if analyst:
        job = dict(name=analyst.analyse_empty,
                   args=[],
                   kwargs={
                       'presenter': presenter,
                       'project_id': project_id
                   },
                   timeout=timeout,
                   queue='high')
        enqueue_job(job)


def analyse_single(result_id, presenter):
    """Queue a single result for analysis."""
    if analyst:
        job = dict(name=analyst.analyse,
                   args=[],
                   kwargs={
                       'presenter': presenter,
                       'result_id': result_id,
                       'silent': False
                   },
                   timeout=current_app.config.get('TIMEOUT'),
                   queue='high')
        enqueue_job(job)
