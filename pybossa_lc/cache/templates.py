# -*- coding: utf8 -*-
"""Test  analysis."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def reset(user_id):
    """Reset the cache for a user."""
    delete_memoized(get_all, user_id)


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_all(user_id):
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


def get_by_id(user_id, tmpl_id):
    """Return templates that the user owns or co-owns."""
    all_tmpl = get_all(user_id)
    filtered = [tmpl for tmpl in all_tmpl if tmpl['id'] == tmpl_id]
    return filtered[0] if filtered else None
