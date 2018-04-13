# -*- coding: utf8 -*-
"""API annotations module for pybossa-lc."""

import json
from flask import Blueprint, abort, make_response, request, current_app
from werkzeug.exceptions import default_exceptions
from pybossa.core import project_repo

from ..cache import annotations as annotations_cache


BLUEPRINT = Blueprint('lc_annotations', __name__)


def jsonld_response(body, status_code=200):
    """Return a valid JSON-LD annotation response.

    See https://www.w3.org/TR/annotation-protocol/#annotation-retrieval
    """
    response = make_response(json.dumps(body), status_code)

    profile = '"http://www.w3.org/ns/anno.jsonld"'
    response.mimetype = 'application/ld+json; profile={0}'.format(profile)

    print 'making response'
    print response.mimetype

    response.status_code = status_code
    return response


def jsonld_abort(status_code):
    """Abort wtih valid JSON-LD response."""
    body = {'code': status_code}

    if status_code in default_exceptions:
        body['message'] = default_exceptions[status_code].description
    else:
        body['message'] = 'Server Error'

    res = jsonld_response(body, status_code=status_code)
    abort(res, status_code)


@BLUEPRINT.route('/wa/<annotation_id>')
def get_wa(annotation_id):
    """Return a Web Annotation."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    full_id = '{0}/lc/annotations/wa/{1}'.format(spa_server_name,
                                                 annotation_id)
    anno = annotations_cache.get(full_id)
    print full_id
    if not anno:
        jsonld_abort(404)

    return jsonld_response(anno)
