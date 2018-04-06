# -*- coding: utf8 -*-
"""Results cache module."""

from sqlalchemy import text
from pybossa.core import db


session = db.slave_session


def get_unanalysed_by_category():
    """Return a summary of unanalysed results for each category."""
    sql = text('''SELECT category.id, category.name,
                  count(result.id) AS n_unanalysed
                  FROM result, project, category
                  WHERE result.project_id = project.id
                  AND result.info IS NULL
                  AND category.id = project.category_id
                  GROUP BY category.id;''')
    db_results = session.execute(sql)
    data = []
    for row in db_results:
        data.append({
            'id': row.id,
            'name': row.name,
            'n_unanalysed': row.n_unanalysed
        })
    return data
