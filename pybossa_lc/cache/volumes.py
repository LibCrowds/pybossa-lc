# -*- coding: utf8 -*-
"""Volumes cache module."""

import json
from sqlalchemy import text
from pybossa.core import db


session = db.slave_session


def get_tmpl_results(volume_id):
    """Return a enhanced results data against template IDs for a volume."""
    sql = text('''SELECT result.id, result.task_id, result.task_run_ids,
               result.project_id, result.created, result.last_version,
               result.info,
               project.info->'template_id' AS template_id,
               task.info->'link' AS link,
               task.state AS task_state
               FROM result, project, category, task
               WHERE result.project_id = project.id
               AND task.id = result.task_id
               AND project.category_id = category.id
               AND project.info->'volume_id' @> :volume_id
               ''')
    db_results = session.execute(sql, dict(volume_id=json.dumps(volume_id)))
    data = {}
    for row in db_results:
        tmpl_id = row.template_id
        result = dict(id=row.id,
                      task_id=row.task_id,
                      task_run_ids=row.task_run_ids,
                      project_id=row.project_id,
                      created=row.created,
                      task_state=row.task_state,
                      link=row.link,
                      info=row.info or {})
        tmpl_results = data.get(tmpl_id, [])
        tmpl_results.append(result)
        data[tmpl_id] = tmpl_results
    return data
