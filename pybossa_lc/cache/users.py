# -*- coding: utf8 -*-
"""Test  analysis."""

from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize


session = db.slave_session


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_user_templates(user_id):
    """Return templates that the user owns or co-owns."""
    sql = text('''SELECT info->>'templates'
                  FROM "user"
                  WHERE "user".id=:user_id
                  OR (info->'templates'->'coowners')::jsonb ? :user_id
                  ''')
    return session.execute(sql, dict(user_id=user_id))
