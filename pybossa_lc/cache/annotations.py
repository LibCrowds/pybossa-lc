# -*- coding: utf8 -*-
"""Annotations cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts


session = db.slave_session


def search(**kwargs):
    """Search annotations."""
    sql = text('''SELECT coalesce(
                 case
                   when (info)::jsonb IS NULL then null
                   else (info->>'annotations')
                 end,
                 'No annotations')
                 FROM "result" LIMIT 100''')
    result = session.execute(sql)
    data = []
    for row in result:
        data += json.loads(row.annotations) if row.annotations else []
    return data
