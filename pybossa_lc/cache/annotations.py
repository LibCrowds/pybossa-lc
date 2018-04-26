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

def search_by_category(category_id, query=None, limit=None, order_by=None):
    """Search annotations by category."""
    if not query:
        query = {}

    if not order_by:
        order_by = 'created'

    result_query = {"annotations": [query]}

    sql = text(
        '''
        WITH annotations AS (
            SELECT jsonb_array_elements(result.info->'annotations') AS anno
            FROM result, project, category
            WHERE result.project_id = project.id
            AND category.id = :category_id
            AND project.category_id = category.id
            AND result.info @> :result_query
        ), total AS (
          SELECT count(*) AS count FROM annotations
        )
        SELECT annotations.anno, total.count
        FROM annotations, total
        WHERE annotations.anno @> :query
        ORDER BY annotations.anno->>:order_by
        LIMIT :limit
        '''
    )
    results = session.execute(sql, dict(category_id=json.dumps(category_id),
                                        result_query=json.dumps(result_query),
                                        query=json.dumps(query), limit=limit,
                                        order_by=order_by))
    annotations = []
    count = 0
    for row in results:
        count = row.count
        annotations.append(row.anno)
    return dict(annotations=annotations, count=count)
