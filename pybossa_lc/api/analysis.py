# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from flask import Blueprint, request, current_app, abort, make_response
from pybossa.core import csrf
from pybossa.core import project_repo, result_repo
from pybossa.auth import ensure_authorized_to
from pybossa.jobs import enqueue_job

from ..jobs import analyse_all, analyse_empty, analyse_single

BLUEPRINT = Blueprint('analysis', __name__)


def respond(msg):
    """Return a basic 200 OK response."""
    data = dict(message=msg, status=200)
    response = make_response(json.dumps(data))
    response.mimetype = 'application/json'
    response.status_code = 200
    return response

def trigger_analysis(presenter):
    """Trigger analysis for a result or set of results."""
    payload = request.json or {}
    short_name = payload.get('project_short_name')

    # Analyse all or empty
    if payload.get('all') or payload.get('empty'):
        project = project_repo.get_by_shortname(short_name)
        if not project:
            abort(404)

        ensure_authorized_to('update', project)

        if payload.get('all'):
            analyse_all(project.id, 'presenter')
        elif payload.get('empty'):
            analyse_empty(project.id, 'presenter')

        return respond('OK')

    # Analyse single
    if payload.get('event') != 'task_completed':
        abort(400)

    result_id = payload['result_id']
    analyse_single(result_id, presenter)
    return respond('OK')



@csrf.exempt
@BLUEPRINT.route('/z3950', methods=['GET', 'POST'])
def z3950_analysis():
    """Endpoint for Z39.50 webhooks."""
    if request.method == 'GET':
        return respond('The Z39.50 endpoint is listening...')
    return trigger_analysis('z3950')


@csrf.exempt
@BLUEPRINT.route('/iiif-annotation', methods=['GET', 'POST'])
def iiif_annotation_analysis():
    """Endpoint for IIIF Annotation webhooks."""
    if request.method == 'GET':
        return respond('The IIIF Annotation endpoint is listening...')
    return trigger_analysis('iiif-annotation')
