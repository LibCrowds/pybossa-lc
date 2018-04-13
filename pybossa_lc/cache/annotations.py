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


def get_by_volume(volume_id, motivation=None):
    """Return all annotations for a volume."""
    m_query = {"annotations": []}
    if motivation:
        m_query['annotations'] = [{'motivation': motivation}]

    sql = text('''SELECT result.info->'annotations' AS annotations
               FROM result, project
               WHERE result.project_id = project.id
               AND project.info->'volume_id' @> :volume_id
               AND result.info @> :m_query
               ''')
    results = session.execute(sql, dict(volume_id=json.dumps(volume_id),
                                        m_query=json.dumps(m_query)))
    annotations = []
    for row in results:
        valid_annos = [anno for anno in row.annotations
                       if not motivation or anno['motivation'] == motivation]
        annotations += valid_annos
    return annotations
