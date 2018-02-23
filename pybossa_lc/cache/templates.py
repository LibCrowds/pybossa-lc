# -*- coding: utf8 -*-
"""Templates cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def reset():
    """Reset the cache."""
    delete_memoized(get_approved)
    delete_memoized(get_pending)


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_all():
    """Return all templates."""
    tmpl_query = json.dumps([{"pending": True}])
    sql = text('''SELECT info->>'templates' AS templates
               FROM "user"
               ''')
    db_results = session.execute(sql, dict(tmpl_query=tmpl_query))
    templates = []
    for row in db_results:
        templates += json.loads(row.templates) if row.templates else []
    return templates


@memoize(timeout=timeouts.get('CATEGORY_TIMEOUT'))
def get_approved():
    """Return approved templates."""
    sql = text('''SELECT info->>'approved_templates' AS templates
               FROM category
               ''')
    result = session.execute(sql)
    templates = []
    for row in result:
        templates += json.loads(row.templates) if row.templates else []
    return templates


@memoize(timeout=timeouts.get('USER_TIMEOUT'))
def get_pending():
    """Return pending templates."""
    tmpl_query = json.dumps([{"pending": True}])
    sql = text('''SELECT info->>'templates' AS templates
               FROM "user"
               WHERE info->'templates' @> :tmpl_query
               ''')
    db_results = session.execute(sql, dict(tmpl_query=tmpl_query))
    templates = []
    for row in db_results:
        templates += [tmpl for tmpl in json.loads(row.templates)
                      if tmpl.get('pending')]
    return templates


def get_by_id(tmpl_id):
    """Return a template by ID."""
    all_tmpl = get_all()
    filtered = [tmpl for tmpl in all_tmpl if tmpl['id'] == tmpl_id]
    return filtered[0] if filtered else None


def get_by_category_id(category_id):
    """Return all templates for a category."""
    all_tmpl = get_all()
    return [tmpl for tmpl in all_tmpl
            if tmpl['category_id'] == category_id]


def get_owner(tmpl_id):
    """Return the owner of a template."""
    tmpl_query = json.dumps([{"id": tmpl_id}])
    sql = text('''SELECT id, name, fullname
               FROM "user"
               WHERE info->'templates' @> :tmpl_query
               ''')
    db_results = session.execute(sql, dict(tmpl_query=tmpl_query))
    for row in db_results:
        return dict(id=row.id,
                    name=row.name,
                    fullname=row.fullname)
    return None
