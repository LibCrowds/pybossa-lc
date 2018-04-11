# -*- coding: utf8 -*-
"""API annotations module for pybossa-lc."""

import json
from flask import Blueprint, abort, make_response, request

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
    anno = annotations_cache.get(request.url)
    print request.path
    if not anno:
        abort(404)

    return json_response(anno)
