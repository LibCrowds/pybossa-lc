# -*- coding: utf8 -*-
"""API annotations module for pybossa-lc."""

import json
from flask import Blueprint, abort, make_response, request, current_app
from pybossa.core import project_repo

from ..cache import annotations as annotations_cache


BLUEPRINT = Blueprint('lc_annotations', __name__)


def json_response(data):
    """Return a json response."""
    response = make_response(json.dumps(data))
    response.mimetype = 'application/json'
    response.status_code = 200
    return response


@BLUEPRINT.route('/wa/<annotation_id>')
def get_wa(annotation_id):
    """Return a Web Annotation."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    full_id = '{0}/lc/annotations/wa/{1}'.format(spa_server_name,
                                                 annotation_id)
    print 'full id', full_id
    anno = annotations_cache.get(full_id)
    if not anno:
        abort(404)

    return json_response(anno)


@BLUEPRINT.route('/wa/<short_name>/custom/<collection_id>',
                 defaults={'page': 1})
@BLUEPRINT.route('/wa/<short_name>/custom/<collection_id>/<int:page>')
def get_custom_collection(short_name, collection_id, page):
    """Return a Web Annotation collection for a custom export format."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)



@BLUEPRINT.route('/wa/<short_name>/volume/<collection_id>',
                 defaults={'page': 1})
@BLUEPRINT.route('/wa/<short_name>/volume/<collection_id>/<int:page>')
def get(collection_id):
    """Return a Web Annotation collection for a volume."""
    category = project_repo.get_category_by(short_name=short_name)
    if not category:  # pragma: no cover
        abort(404)
