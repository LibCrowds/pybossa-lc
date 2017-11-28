# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from rq import Queue
from flask import Blueprint, request, current_app, abort, make_response
from pybossa_lc.analysis import z3950, libcrowds_viewer
from pybossa.core import sentinel


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


def analyse(analysis_func, analysis_all_func):
    """Queue analysis for a result or set of results."""
    payload = request.json or {}

    # Set job type
    job = analysis_func
    msg = 'Result added to job queue'
    if request.args.get('project_short_name') and request.args.get('all'):
        payload['project_short_name'] = request.args.get('project_short_name')
        job = analysis_all_func
        msg = 'All results added to job queue'

    # Check webhook event
    elif payload.get('event') != 'task_completed':
        err_msg = 'This is not a task_completed event'
        abort(400, err_msg)

    # Check auth
    ensure_authorized_to('update', project)

    # Queue the job
    redis_conn = sentinel.master
    queue = Queue('low', connection=redis_conn)
    queue.enqueue(job, timeout=10*MINUTE, **payload)

    return respond(payload['project_short_name'], msg)


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
