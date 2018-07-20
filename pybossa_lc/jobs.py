# -*- coding: utf8 -*-
"""Jobs module for pybossa-lc."""

import errno
from flask import current_app
from pybossa.jobs import enqueue_job, import_tasks
from pybossa.core import task_repo, project_repo
from socket import error as socket_error

from .analysis.analyst import Analyst


MINUTE = 60
HOUR = 60 * MINUTE


def analyse_all(project_id, presenter):
    """Queue analysis of all results for a project."""
    timeout = 1 * HOUR
    analyst = Analyst()
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
    analyst = Analyst()
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
    analyst = Analyst()
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


def import_tasks_with_redundancy(project_id, n_answers, **import_data):
    """Import tasks then set redundancy."""
    try:
        import_tasks(project_id, **import_data)
    except socket_error as serr:
        # Because sending emails will fail during development
        if serr.errno != errno.ECONNREFUSED:
            raise serr
    project = project_repo.get(project_id)
    task_repo.update_tasks_redundancy(project, int(n_answers))
