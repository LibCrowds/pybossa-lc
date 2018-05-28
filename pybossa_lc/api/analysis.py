# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from flask import Blueprint, request, abort, make_response
from pybossa.core import csrf
from pybossa.core import project_repo
from pybossa.auth import ensure_authorized_to

from ..jobs import analyse_all, analyse_empty, analyse_single


BLUEPRINT = Blueprint('lc_analysis', __name__)


def respond(msg):
    """Return a basic 200 OK response."""
    data = dict(message=msg, status=200)
    response = make_response(json.dumps(data))
    response.mimetype = 'application/json'
    response.status_code = 200
    return response


@csrf.exempt
@BLUEPRINT.route('/', methods=['GET', 'POST'])
def analyse():
    """Trigger analysis for a result or set of results."""
    if request.method == 'GET':
        return respond('The analysis endpoint is listening...')

    payload = request.json or {}
    short_name = payload.get('project_short_name')
    project = project_repo.get_by_shortname(short_name)
    if not project:  # pragma: no cover
        abort(404)

    category = project_repo.get_category(project.category_id)
    presenter = category.info.get('presenter')
    valid_presenters = ['z3950', 'iiif-annotation']
    if not presenter or presenter not in valid_presenters:
        abort(400, 'Invalid task presenter')

    # Analyse all or empty
    if payload.get('all') or payload.get('empty'):
        ensure_authorized_to('update', project)

        if payload.get('all'):
            analyse_all(project.id, presenter)
        elif payload.get('empty'):
            analyse_empty(project.id, presenter)

        return respond('OK')

    # Analyse single
    if payload.get('event') != 'task_completed':
        abort(400)

    result_id = payload['result_id']
    analyse_single(result_id, presenter)
    return respond('OK')
