# -*- coding: utf8 -*-
"""Test  analysis."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize


session = db.slave_session


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_user_templates(user_id):
    """Return templates that the user owns or co-owns."""
    sql = text('''SELECT info->>'templates' AS templates,
                  json_array_elements((info->>'templates')::jsonb) AS bar
                  FROM "user"
                  ''')
    print sql
    result = session.execute(sql, dict(user_id=user_id))
    templates = []
    for row in result:
        print row
        templates += json.loads(row.templates) if row.templates else []
    return templates
