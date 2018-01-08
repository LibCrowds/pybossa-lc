# -*- coding: utf8 -*-
"""Templates cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def reset():
    """Reset the cache."""
    delete_memoized(get_all)

@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_all():
    """Return all templates."""
    sql = text('''SELECT info->>'templates' AS templates FROM "user"''')
    result = session.execute(sql)
    templates = []
    for row in result:
        templates += json.loads(row.templates) if row.templates else []
    return templates


def get_by_id(tmpl_id):
    """Return a template by ID."""
    all_tmpl = get_all()
    filtered = [tmpl for tmpl in all_tmpl if tmpl['id'] == tmpl_id]
    return filtered[0] if filtered else None
