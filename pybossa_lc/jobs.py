# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

from flask import current_app
from pybossa.core import project_repo, announcement_repo
from pybossa.model.announcement import Announcement
from pybossa.jobs import enqueue_job

from .utils import get_analyst
from . import project_tmpl_repo


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
    if extra_startup_tasks.get('populate_empty_results'):
        enqueue_job({
            'name': populate_empty_results,
            'args': [],
            'kwargs': {},
            'timeout': current_app.config.get('TIMEOUT'),
            'queue': 'medium'
        })
    if extra_startup_tasks.get('reanalyse_all_results'):
        enqueue_job({
            'name': reanalyse_all_results,
            'args': [],
            'kwargs': {},
            'timeout': current_app.config.get('TIMEOUT'),
            'queue': 'medium'
        })
    if extra_startup_tasks.get('remove_bad_volumes'):
        enqueue_job({
            'name': remove_bad_volumes,
            'args': [],
            'kwargs': {},
            'timeout': current_app.config.get('TIMEOUT'),
            'queue': 'low'
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


def populate_empty_results():
    """Populate any empty results"""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    for category in categories:
        presenter = category.info.get('presenter')
        cat_projects = project_repo.filter_by(category_id=category.id)
        for project in cat_projects:
            analyst = get_analyst(presenter)
            analyst.analyse_empty(project.id)


def reanalyse_all_results():
    """Reanalyse all results"""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    for category in categories:
        presenter = category.info.get('presenter')
        cat_projects = project_repo.filter_by(category_id=category.id)
        for project in cat_projects:
            analyst = get_analyst(presenter)
            analyst.analyse_all(project.id)


def remove_bad_volumes():
    """Remove volumes that don't comply with the correct data structure."""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    required = ['id', 'name', 'source', 'short_name']
    for category in categories:
        if not isinstance(category.info, dict):
            category.info = {}

        volumes = category.info.get('volumes', [])
        if not isinstance(volumes, list):
            volumes = []

        vols = [v for v in volumes if all(key in v.keys() for key in required)]

        category.info['volumes'] = vols
        project_repo.update_category(category)


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
    analyst = get_analyst(presenter)
    timeout = 1 * HOUR
    if analyst:
        job = dict(name=analyst.analyse_all,
                   args=[],
                   kwargs={'project_id': project_id},
                   timeout=timeout,
                   queue='high')
        enqueue_job(job)


def analyse_empty(project_id, presenter):
    """Queue analysis of all empty results for a proejct."""
    analyst = get_analyst(presenter)
    timeout = 1 * HOUR
    if analyst:
        job = dict(name=analyst.analyse_empty,
                   args=[],
                   kwargs={'project_id': project_id},
                   timeout=timeout,
                   queue='high')
        enqueue_job(job)


def analyse_single(result_id, presenter):
    """Queue a single result for analysis."""
    analyst = get_analyst(presenter)
    if analyst:
        job = dict(name=analyst.analyse,
                   args=[],
                   kwargs={'result_id': result_id, 'silent': False},
                   timeout=current_app.config.get('TIMEOUT'),
                   queue='high')
        enqueue_job(job)
