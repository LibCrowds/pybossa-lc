# -*- coding: utf8 -*-
"""Results cache module."""

import json
from sqlalchemy import text
from pybossa.core import db


session = db.slave_session


def get_unanalysed_by_category():
    """Return a summary of unanalysed results for each category."""
    sql = text('''SELECT category.id, category.name,
                  count(result.id) AS n_unanalysed
                  FROM result
                  RIGHT JOIN project ON project.id = result.project_id
                  INNER JOIN category ON category.id = project.category_id
                  WHERE result.info IS NULL
                  AND result.project_id = project.id
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


def get_by_template(template_id):
    """Return a enhanced results data against template IDs for a volume."""
    sql = text('''SELECT result.id, result.task_id, result.task_run_ids,
               result.project_id, result.created, result.last_version,
               result.info,
               task.info->'link' AS link,
               task.state AS task_state
               FROM result, project, category, task
               WHERE result.project_id = project.id
               AND task.id = result.task_id
               AND project.category_id = category.id
               AND project.info->'template_id' @> :template_id
               ''')
    params = dict(template_id=json.dumps(template_id))
    db_results = session.execute(sql, params)
    data = {}
    for row in db_results:
        tmpl_id = row.template_id
        result = dict(id=row.id,
                      task_id=row.task_id,
                      task_run_ids=row.task_run_ids,
                      project_id=row.project_id,
                      created=row.created,
                      last_version=row.last_version,
                      task_state=row.task_state,
                      link=row.link,
                      info=row.info or {})
        tmpl_results = data.get(tmpl_id, [])
        tmpl_results.append(result)
        data[tmpl_id] = tmpl_results
    return data
