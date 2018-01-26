# -*- coding: utf8 -*-
"""API annotations search module for pybossa-lc."""

import json
from flask import Response, Blueprint
from pybossa.core import csrf


BLUEPRINT = Blueprint('annotations', __name__)


@csrf.exempt
@BLUEPRINT.route('/search')
def search():
    """Search the annotations."""
    data = dict()
    return Response(json.dumps(data), 200, mimetype='application/json')
