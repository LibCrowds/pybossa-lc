# -*- coding: utf8 -*-
"""Annotations cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def get(id):
    """Return an annotation by ID."""
    anno_query = json.dumps([{"id": id}])
    sql = text('''SELECT info->>'annotations' AS annotations
               FROM result
               WHERE info->'annotations' @> :anno_query
               ''')
    db_results = session.execute(sql, dict(anno_query=anno_query))
    for row in db_results:
        annotations = json.loads(row.annotations)
        return [anno for anno in annotations if anno['id'] == id][0]
