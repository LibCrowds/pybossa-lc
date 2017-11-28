# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from rq import Queue
from flask import Blueprint, request, current_app, abort, make_response
from pybossa_lc.analysis import z3950, libcrowds_viewer
from pybossa.core import sentinel
from pybossa.core import project_repo, result_repo
from pybossa.auth import ensure_authorized_to


BLUEPRINT = Blueprint('analysis', __name__)
MINUTE = 60
HOUR = 60*MINUTE


def respond(msg, short_name):
    """Return a basic 200 response."""
    response = make_response(
        json.dumps({
            "message": msg,
            "project": short_name,
            "status": 200,
        })
    )
    response.mimetype = 'application/json'
    response.status_code = 200
    return


def queue_job(job, timeout, arg):
    """Add an analysis job to the queue."""
    redis_conn = sentinel.master
    queue = Queue('low', connection=redis_conn)
    queue.enqueue(job, timeout=timeout, args=(arg))


def analyse_all(short_name, func):
    """Queue analysis of all results.

    Requires the current user to be authorised to update the project.
    """
    project = project_repo.get_by_shortname(short_name)
    if not project:
        abort(404)

    ensure_authorized_to('update', project)

    results = result_repo.filter_by(project_id=project.id)
    queue_job(func, 12*HOUR, results)
    return respond(project.short_name, 'All results added to job queue')



def analyse(analysis_func, analysis_all_func):
    """Queue analysis for a result or set of results."""
    payload = request.json or {}

    if request.args.get('project_short_name') and request.args.get('all'):
        short_name = request.args.get('project_short_name')
        return analyse_all(short_name, analysis_all_func)

    elif payload.get('event') != 'task_completed':
        err_msg = 'This is not a task_completed event'
        abort(400, err_msg)

    result = result_repo.get(payload['result_id'])

    # If the result isn't empty, check if the current user is authorized
    if not result.info:
        ensure_authorized_to('update', result)

    queue_job(analysis_func, 10*MINUTE, result)
    return respond(payload['project_short_name'], 'Results added to job queue')


@BLUEPRINT.route('z3950', methods=['GET', 'POST'])
def z3950_analysis():
    """Endpoint for Z39.50 webhooks."""
    if request.method == 'GET':
        return respond(None, 'The Z39.50 endpoint is listening...')
    return analyse(z3950.analyse, z3950.analyse_all)


@BLUEPRINT.route('libcrowds-viewer', methods=['GET', 'POST'])
def libcrowds_viewer_analysis():
    """Endpoint for LibCrowds Viewer webhooks."""
    if request.method == 'GET':
        return respond(None, 'The LibCrowds Viewer endpoint is listening...')
    return analyse(libcrowds_viewer.analyse, libcrowds_viewer.analyse_all)
