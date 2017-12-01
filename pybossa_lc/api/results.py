# -*- coding: utf8 -*-
"""API analysis module for pybossa-lc."""

import json
from flask import Response, Blueprint
from pybossa.core import csrf

from ..cache import results as results_cache


BLUEPRINT = Blueprint('results', __name__)


@csrf.exempt
@BLUEPRINT.route('/empty')
def empty():
    """List any projects with unanalysed results."""
    data = results_cache.empty_results
    return Response(json.dumps(data), 200, mimetype='application/json')
