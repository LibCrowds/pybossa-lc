# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

from flask import current_app
from pybossa.core import project_repo, announcement_repo
from pybossa.cache.projects import overall_progress
from pybossa.model.announcement import Announcement
from pybossa.jobs import enqueue_job

from .cache import templates as templates_cache
from .analysis import z3950, iiif_annotation


def queue_startup_jobs():
    """Queue startup jobs."""
    jobs = [
        dict(name=check_for_missing_templates,
             args=[],
             kwargs={},
             timeout=current_app.config.get('TIMEOUT'),
             queue='high'),
        dict(name=populate_empty_results,
             args=[],
             kwargs={},
             timeout=current_app.config.get('TIMEOUT'),
             queue='high')
    ]
    for job in jobs:
        enqueue_job(job)


def check_for_missing_templates():
    """Make an announcement if any projects are missing templates."""
    from pybossa.core import project_repo
    projects = project_repo.get_all()
    templates = templates_cache.get_all()
    template_ids = [tmpl['id'] for tmpl in templates]
    for project in projects:
        project_tmpl_id = project.info.get('template_id')
        if not project_tmpl_id or project_tmpl_id not in template_ids:
            tmpl_endpoint = current_app.config.get('PROJECT_TMPL_ENDPOINT')
            endpoint = tmpl_endpoint.format(project.short_name)
            url = get_launch_url(endpoint)
            make_announcement('Missing Template', project.name, url,
                              admin=True)


def populate_empty_results():
    """Populate any empty results"""
    from pybossa.core import project_repo
    categories = project_repo.get_all_categories()
    for category in categories:
        presenter = category.info.get('presenter')
        cat_projects = project_repo.filter_by(category_id=category.id)
        for project in cat_projects:
            if presenter == 'iiif-annotation':
                iiif_annotation.analyse_empty(project.short_name)
            elif presenter == 'z3950':
                z3950.analyse_empty(project.short_name)


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
