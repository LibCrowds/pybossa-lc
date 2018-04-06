# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

from flask import current_app
from pybossa.core import project_repo, announcement_repo
from pybossa.model.announcement import Announcement
from pybossa.jobs import enqueue_job

from . import project_tmpl_repo, analyst


HOUR = 60 * 60


def queue_startup_jobs():
    """Queue startup jobs."""
    extra_startup_tasks = current_app.config.get('EXTRA_STARTUP_TASKS')
    if extra_startup_tasks.get('check_for_invalid_templates'):
        enqueue_job({
            'name': check_for_invalid_templates,
            'args': [],
            'kwargs': {},
            'timeout': current_app.config.get('TIMEOUT'),
            'queue': 'high'
        })


def check_for_invalid_templates():
    """Make an announcement if any projects have invalid templates."""
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
                tmpl_endpoint = current_app.config.get('PROJECT_TMPL_ENDPOINT')
                endpoint = tmpl_endpoint.format(project.short_name)
                url = get_launch_url(endpoint)
                make_announcement('Invalid Template', project.name, url,
                                  admin=True)


def make_announcement(title, body, url, media_url=None, admin=False):
    """Make an annoucement."""
    from pybossa.core import announcement_repo
    announcement_user_id = current_app.config.get('ANNOUNCEMENT_USER_ID')
    if not announcement_user_id:
        return

    announcement = Announcement(user_id=announcement_user_id,
                                title=title,
                                body=body,
                                published=True,
                                media_url=media_url,
                                info={
                                    'admin': admin,
                                    'url': url
                                })
    announcement_repo.save(announcement)


def get_launch_url(endpoint):
    """Get a frontend launch URL for announcements and push notifications."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    if not spa_server_name:
        return None
    return spa_server_name + endpoint


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
