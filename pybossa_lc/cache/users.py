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
    sql = text('''SELECT info->>'templates' AS templates
                  FROM "user"
                  WHERE id = :user_id
                  OR (info->>'templates')::jsonb @>
                  '[{"project": {"coowners": [:user_id]}}]'
                  ''')
    result = session.execute(sql, dict(user_id=user_id))
    templates = []
    for row in result:
        templates += json.loads(row.templates) if row.templates else []
    return templates


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_user_template_by_id(user_id, tmpl_id):
    """Return templates that the user owns or co-owns."""
    sql = text('''SELECT info->>'templates' AS templates
                  FROM "user"
                  WHERE id = :user_id
                  OR (info->>'templates')::jsonb @>
                  '[{"project": {"coowners": [:user_id]}}]'
                  AND (info->>'templates')::jsonb @> '[{"id": "':tmpl_id'"}]'
                  LIMIT 1
                  ''')
    result = session.execute(sql, dict(user_id=user_id, tmpl_id=tmpl_id))
    for row in result:
        if row.templates is not None:
            return json.loads(row.templates)[0]
        else:  # pragma: no cover
            return None
