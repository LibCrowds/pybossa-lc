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


def search_by_category(category_id, contains=None, limit=None, offset=None,
                       order_by=None):
    """Search annotations by category."""
    if not contains:
        contains = {}

    if not order_by:
        order_by = 'created'

    r_contains = {"annotations": [contains]}

    sql = text(
        '''
        WITH annotations AS (
            SELECT jsonb_array_elements(result.info->'annotations') AS anno
            FROM result, project, category
            WHERE result.project_id = project.id
            AND category.id = :category_id
            AND project.category_id = category.id
            AND result.last_version = True
            AND result.info @> :r_contains
        ), total AS (
          SELECT count(*) AS count FROM annotations
        )
        SELECT annotations.anno, total.count
        FROM annotations, total
        WHERE annotations.anno @> :contains
        ORDER BY annotations.anno->>:order_by
        LIMIT :limit
        OFFSET :offset
        '''
    )
    results = session.execute(sql, dict(category_id=json.dumps(category_id),
                                        r_contains=json.dumps(r_contains),
                                        contains=json.dumps(contains),
                                        limit=limit, offset=offset,
                                        order_by=order_by))
    annotations = []
    count = 0
    for row in results:
        count = row.count
        annotations.append(row.anno)
    return dict(annotations=annotations, count=count)
