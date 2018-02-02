# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

from rq import Queue
from flask import current_app
from pybossa.core import sentinel
from pybossa.core import project_repo, announcement_repo
from pybossa.cache.projects import overall_progress
from pybossa.model.announcement import Announcement

from .cache import templates as templates_cache


PROJECT_TMPL_ENDPOINT = '/admin/project/{}/template'


def queue_startup_jobs():
    """Queue startup jobs."""
    timeout = current_app.config.get('TIMEOUT')
    redis_conn = sentinel.master
    queue = Queue('low', connection=redis_conn)
    queue.enqueue_call(func=check_for_missing_templates, timeout=timeout)


def check_for_missing_templates():
        """Make an announcement if any projects are missing templates."""
        projects = project_repo.get_all()
        templates = templates_cache.get_all()
        template_ids = [tmpl['id'] for tmpl in templates]
        for project in projects:
            project_tmpl_id = project.info.get('template_id')
            if not project_tmpl_id or project_tmpl_id not in template_ids:
                body = 'Set a valid template for {}'.format(project.name)
                endpoint = PROJECT_TMPL_ENDPOINT.format(project.short_name)
                url = get_launch_url(endpoint)
                make_announcement('Missing Template', body, url, admin=True)


def make_announcement(title, body, url, media_url=None, admin=False):
    """Make an annoucement."""
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
