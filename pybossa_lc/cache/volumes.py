# -*- coding: utf8 -*-
"""Volumes cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def get_results_by_volume(volume_id):
    """Return all transcribed results by volume."""
    sql = text('''SELECT result.id, result.task_id, result.task_run_ids,
               result.project_id, result.last_version, result.created,
               result.info
               FROM result, project
               WHERE (project.info->>'volume_id') = :volume_id
               AND project.id = result.project_id;''')
    data = session.execute(sql, dict(volume_id=volume_id))
    results = []
    for row in data:
        result = dict(id=row.id, task_id=row.task_id,
                      task_run_ids=row.task_run_ids, project_id=row.project_id,
                      last_version=row.last_version, created=row.created,
                      info=row.info)
        results.append(result)
    return results
