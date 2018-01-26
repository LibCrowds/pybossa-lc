# -*- coding: utf8 -*-
"""API annotations search module for pybossa-lc."""

import json
from flask import Response, Blueprint, request
from pybossa.core import csrf

from ..cache import annotations as annotations_cache


BLUEPRINT = Blueprint('annotations', __name__)


@csrf.exempt
@BLUEPRINT.route('/search')
def search():
    """Search the annotations."""
    results = annotations_cache.search(**request.args)
    data = dict()
    return Response(json.dumps(data), 200, mimetype='application/json')
