# -*- coding: utf8 -*-
"""API annotations module for pybossa-lc."""

import json
from flask import Blueprint, abort, make_response, request, current_app

from ..cache import annotations as annotations_cache


BLUEPRINT = Blueprint('lc_annotations', __name__)


def json_response(data):
    """Return a json response."""
    response = make_response(json.dumps(data))
    response.mimetype = 'application/json'
    response.status_code = 200
    return response


@BLUEPRINT.route('/<annotation_id>')
def get(annotation_id):
    """Return an annotation."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    full_id = '{0}/lc/annotations/{1}'.format(spa_server_name, annotation_id)
    anno = annotations_cache.get(full_id)
    if not anno:
        abort(404)

    return json_response(anno)
