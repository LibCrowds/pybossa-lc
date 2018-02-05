# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from flask import Blueprint, request, current_app, abort, make_response
from pybossa.core import csrf
from pybossa.core import project_repo, result_repo
from pybossa.auth import ensure_authorized_to
from pybossa.jobs import enqueue_job

from ..analysis import z3950, iiif_annotation


BLUEPRINT = Blueprint('analysis', __name__)


def respond(msg, **kwargs):
    """Return a basic 200 response."""
    data = dict(message=msg, status=200)
    data.update(kwargs)
    response = make_response(json.dumps(data))
    response.mimetype = 'application/json'
    response.status_code = 200
    return response


def analyse_all(short_name, func):
    """Queue analysis of all results.

    Requires the current user to be authorised to update the project.
    """
    project = project_repo.get_by_shortname(short_name)
    if not project:
        abort(404)

    ensure_authorized_to('update', project)
    job = dict(name=func,
               args=[],
               kwargs={'project_id': project.id},
               timeout=current_app.config.get('TIMEOUT'),
               queue='high')
    enqueue_job(job)
    return respond('All results added to job queue',
                   project_short_name=project.short_name)


def analyse_empty(short_name, func):
    """Queue analysis of all empty results.

    Requires the current user to be authorised to update the project.
    """
    project = project_repo.get_by_shortname(short_name)
    if not project:
        abort(404)

    ensure_authorized_to('update', project)
    job = dict(name=func,
               args=[],
               kwargs={'project_id': project.id},
               timeout=current_app.config.get('TIMEOUT'),
               queue='high')
    enqueue_job(job)
    return respond('Empty results added to job queue',
                   project_short_name=project.short_name)


def analyse_single(payload, func):
    """Queue a single result for analysis."""
    if payload.get('event') != 'task_completed':
        err_msg = 'This is not a task_completed event'
        abort(400, err_msg)

    result = result_repo.get(payload['result_id'])
    if result.info:
        ensure_authorized_to('update', result)
    job = dict(name=func,
               args=[],
               kwargs={'result_id': result.id},
               timeout=current_app.config.get('TIMEOUT'),
               queue='high')
    enqueue_job(job)
    return respond('Result added to job queue', result_id=result.id,
                   project_short_name=payload['project_short_name'])


def analyse(analysis_func, analysis_all_func, analysis_empty_func):
    """Queue analysis for a result or set of results."""
    payload = request.json or {}
    if payload.get('all'):
        short_name = payload.get('project_short_name')
        return analyse_all(short_name, analysis_all_func)
    elif payload.get('empty'):
        short_name = payload.get('project_short_name')
        return analyse_empty(short_name, analysis_empty_func)
    return analyse_single(payload, analysis_func)


@csrf.exempt
@BLUEPRINT.route('/z3950', methods=['GET', 'POST'])
def z3950_analysis():
    """Endpoint for Z39.50 webhooks."""
    if request.method == 'GET':
        return respond('The Z39.50 endpoint is listening...')
    return analyse(z3950.analyse, z3950.analyse_all, z3950.analyse_empty)


@csrf.exempt
@BLUEPRINT.route('/iiif-annotation', methods=['GET', 'POST'])
def iiif_annotation_analysis():
    """Endpoint for IIIF Annotation webhooks."""
    if request.method == 'GET':
        return respond('The IIIF Annotation endpoint is listening...')
    return analyse(iiif_annotation.analyse, iiif_annotation.analyse_all,
                   iiif_annotation.analyse_empty)
