# -*- coding: utf8 -*-
"""Test  analysis."""

from sqlalchemy import text
from pybossa.core import db
from pybossa.cache import cache, ONE_HOUR


session = db.slave_session


@cache(timeout=ONE_HOUR, key_prefix="empty_results")
def empty_results():
    """List any projects with unanalysed results."""
    sql = text('''SELECT project.short_name, project.name, COUNT(result.id)
                  FROM project, result
                  WHERE project.id = result.project_id
                  AND coalesce(result.info::text, '') = ''
                  GROUP BY project.short_name, project.name;''')
    results = session.execute(sql)
    data = []
    for row in results:
        data.append({
            'name': row.name,
            'short_name': row.short_name,
            'n_empty_results': row.count
        })
    return data
