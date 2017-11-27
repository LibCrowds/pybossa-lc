# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from rq import Queue
from flask import Blueprint, request, current_app, abort, make_response
from .analysis import z3950, libcrowds_viewer
from pybossa.core import sentinel


BLUEPRINT = Blueprint('analysis', __name__)
MINUTE = 60
HOUR = 60*MINUTE


def analyse(func):
    """Analyse a webhook."""
    payload = request.json or {}
    if payload.get('event') != 'task_completed':
        err_msg = 'This is not a task_completed event'
        abort(400, err_msg)

    redis_conn = sentinel.master
    queue = Queue('low', connection=redis_conn)
    queue.enqueue(func, timeout=10*MINUTE, **payload)
    return ok_response()


def analyse_all(func):
    """Analyse all results for a project."""
    payload = request.json or {}
    payload['project_short_name'] = request.args.get('project_short_name')
    redis_conn = sentinel.master
    queue = Queue('low', connection=redis_conn)
    queue.enqueue(func, timeout=10*MINUTE, **payload)
    return ok_response()


def ok_response():
    """Return a basic HTTP 200 response."""
    response = make_response(
        json.dumps({
            "message": "OK",
            "status": 200,
        })
    )
    response.mimetype = 'application/json'
    response.status_code = 200
    return response


@BLUEPRINT.route('convert-a-card', methods=['GET', 'POST'])
def convert_a_card():
    """Endpoint for Convert-a-Card webhooks."""
    if request.method == 'GET':
        return ok_response()

    if request.args.get('project_short_name'):
        return analyse_all(z3950.analyse_all)

    return analyse(z3950.analyse)


@BLUEPRINT.route('playbills/select', methods=['GET', 'POST'])
def playbills_mark():
    """Endpoint for In the Spotlight select task webhooks."""
    if request.method == 'GET':
        return ok_response()

    if request.args.get('project_short_name'):
        return analyse_all(libcrowds_viewer.analyse_all_selections)

    return analyse(libcrowds_viewer.analyse_selections)
