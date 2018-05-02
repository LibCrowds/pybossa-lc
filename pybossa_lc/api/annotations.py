# -*- coding: utf8 -*-
"""Annotations API module for pybossa-lc."""

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
    link = '<http://www.w3.org/ns/ldp#Resource>; rel="type"'
    response.headers['Link'] = link
    response.headers['Allow'] = 'GET,OPTIONS,HEAD'
    response.headers['Vary'] = 'Accept'
    response.add_etag()
    response.status_code = status_code
    return response


def jsonld_abort(status_code, message=None):
    """Abort wtih valid JSON-LD response."""
    body = {'code': status_code}

    if message:
        body['message'] = message
    elif status_code in default_exceptions:
        body['message'] = default_exceptions[status_code].description
    else:
        body['message'] = 'Server Error'

    return jsonld_response(body, status_code=status_code)


def get_anno_collection(count, entity, url_base, query_str=None):
    """Return an Annotation Collection."""
    id_uri = "{0}/{1}".format(url_base, entity.id)
    label = u"{0} Annotations".format(entity.name)

    per_page = current_app.config.get('ANNOTATIONS_PER_PAGE')
    last_page = 0 if count <= 0 else ((count - 1) // per_page) + 1
    first_uri = "{0}/1".format(id_uri)
    last_uri = "{0}/{1}".format(id_uri, last_page)

    if query_str:
        id_uri += "?{}".format(query_str)
        first_uri += "?{}".format(query_str)
        last_uri += "?{}".format(query_str)

    data = {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "id": id_uri,
        "type": "AnnotationCollection",
        "label": label,
        "total": count
    }

    if count > 0:
        data['first'] = first_uri

    if last_page > 1:
        data['last'] = last_uri

    return data


def get_anno_page(annotations, count, entity, url_base, page,
                  query_str=None, iris=False):
    """Return an Annotation Page."""
    anno_collection_uri = "{0}/{1}".format(url_base, entity.id)
    id_uri = "{0}/{1}".format(anno_collection_uri, page)
    next_uri = "{0}/{1}".format(anno_collection_uri, page + 1)

    if query_str:
        anno_collection_uri += "?{}".format(query_str)
        id_uri += "?{}".format(query_str)
        next_uri += "?{}".format(query_str)

    per_page = current_app.config.get('ANNOTATIONS_PER_PAGE')
    last_page = 0 if count <= 0 else ((count - 1) // per_page) + 1
    if page > last_page:
        return None

    items = annotations
    if iris:
        items = [item['id'] for item in items]
    else:
        for item in items:
            add_full_wa_ids(item)

    data = {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "id": id_uri,
        "type": "AnnotationPage",
        "partOf": {
            "id": anno_collection_uri,
            "label": u"{0} Annotations".format(entity.name),
            "total": count
        },
        "startIndex": 0,
        "items": items
    }

    if last_page > page:
        data['next'] = next_uri

    return data


def add_full_wa_ids(annotation):
    """Update WA IDs to link to the current SPA server."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')

    def get_full_id(_id):
        return '{0}/lc/annotations/wa/{1}'.format(spa_server_name, _id)

    annotation['id'] = get_full_id(annotation['id'])
    if isinstance(annotation['body'], list):
        for item in annotation['body']:
            if item['purpose'] == 'linking':
                item['source'] = get_full_id(item['source'])


@BLUEPRINT.route('/wa/<annotation_id>')
def get_wa(annotation_id):
    """Return an Annotation."""
    anno = annotations_cache.get(annotation_id)
    if not anno:
        return jsonld_abort(404)

    add_full_wa_ids(anno)
    return jsonld_response(anno)


@BLUEPRINT.route('/wa/collection/<category_id>')
def get_wa_category_collection(category_id):
    """Return an Annotation Collection for a category."""
    category = project_repo.get_category(category_id)
    if not category:
        return jsonld_abort(404)

    contains = request.args.get('contains')
    if contains:
        try:
            contains = json.loads(contains)
        except ValueError as err:
            msg = err.message
            return jsonld_abort(400, "Invalid contains query - {}".format(msg))

    limit = 1  # We don't need any actual annotations here
    data = annotations_cache.search_by_category(category.id, contains=contains,
                                                limit=limit)

    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    url_base = '{0}/lc/annotations/wa/collection'.format(spa_server_name)

    anno_collection = get_anno_collection(data['count'], category, url_base,
                                          query_str=request.query_string)

    return jsonld_response(anno_collection)


@BLUEPRINT.route('/wa/collection/<category_id>/<int:page>')
def get_wa_category_page(category_id, page):
    """Return an Annotation Page for a category."""
    category = project_repo.get_category(category_id)
    if not category:
        return jsonld_abort(404)

    contains = request.args.get('contains')
    if contains:
        try:
            contains = json.loads(contains)
        except ValueError as err:
            msg = err.message
            return jsonld_abort(400, "Invalid contains query - {}".format(msg))

    default_limit = current_app.config.get('ANNOTATIONS_PER_PAGE')
    limit = request.args.get('limit', default_limit)
    offset = limit * (page - 1)
    order_by = request.args.get('orderby')
    iris = request.args.get('iris')
    data = annotations_cache.search_by_category(category.id, contains=contains,
                                                limit=limit, offset=offset,
                                                order_by=order_by)

    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    url_base = '{0}/lc/annotations/wa/collection'.format(spa_server_name)

    anno_page = get_anno_page(data['annotations'], data['count'], category,
                              url_base, page, query_str=request.query_string,
                              iris=iris)

    if not anno_page:
        return jsonld_abort(404)

    return jsonld_response(anno_page)
