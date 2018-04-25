# -*- coding: utf8 -*-
"""Annotations cache module."""

import json
from sqlalchemy import text
from pybossa.core import db


session = db.slave_session


def get(anno_id):
    """Return an annotation by ID."""
    anno_query = json.dumps([{"id": anno_id}])
    sql = text('''SELECT info->>'annotations' AS annotations
               FROM result
               WHERE info->'annotations' @> :anno_query
               ''')
    db_results = session.execute(sql, dict(anno_query=anno_query))
    for row in db_results:
        annotations = json.loads(row.annotations)
        return [anno for anno in annotations if anno['id'] == anno_id][0]


def get_by_volume(volume_id, query=None):
    """Return annotations for a volume."""
    anno_query = {"annotations": []}
    if query:
        anno_query['annotations'] = [query]

    sql = text('''SELECT result.info->'annotations' AS annotations
               FROM result, project
               WHERE result.project_id = project.id
               AND project.info->'volume_id' @> :volume_id
               AND result.info @> :anno_query
               ''')
    results = session.execute(sql, dict(volume_id=json.dumps(volume_id),
                                        anno_query=json.dumps(anno_query)))
    annotations = []
    for row in results:
        valid_annos = [anno for anno in row.annotations
                       if not query or
                       all(item in anno.items() for item in query.items())]
        annotations += valid_annos
    return annotations

def get_by_category(category_id, query=None):
    """Return annotations for a category."""
    anno_query = {"annotations": []}
    if query:
        anno_query['annotations'] = [query]

    sql = text('''SELECT result.info->'annotations' AS annotations
               FROM result, project, category
               WHERE result.project_id = project.id
               AND category.id = :category_id
               AND project.category_id = category.id
               AND result.info @> :anno_query
               ''')
    results = session.execute(sql, dict(category_id=json.dumps(category_id),
                                        anno_query=json.dumps(anno_query)))
    annotations = []
    for row in results:
        valid_annos = [anno for anno in row.annotations
                       if not query or
                       all(item in anno.items() for item in query.items())]
        annotations += valid_annos
    return annotations