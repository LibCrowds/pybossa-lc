# -*- coding: utf8 -*-
"""Volumes cache module."""

import json
from sqlalchemy import text
from pybossa.core import db, timeouts
from pybossa.cache import memoize, delete_memoized


session = db.slave_session


def get_tmpl_results(volume_id):
    """Return a dict of results data against template IDs for a volume."""
    sql = text('''SELECT result.id, result.task_id, result.task_run_ids,
               result.project_id, result.created, result.last_version,
               result.info,
               project.info->'template_id' AS template_id,
               category.info->'presenter' AS presenter
               FROM result, project, category
               WHERE result.project_id = project.id
               AND project.category_id = category.id
               AND project.info->'volume_id' @> :volume_id
               ''')
    results = session.execute(sql, dict(volume_id=json.dumps(volume_id)))
    data = {}
    for row in results:
        tmpl_id = row.template_id
        result = dict(id=row.id,
                      task_id=row.task_id,
                      task_run_ids=row.task_run_ids,
                      project_id=row.project_id,
                      created=row.created,
                      last_version=row.last_version,
                      info=row.info or {})
        data_row = data.get(tmpl_id, {})
        results_data = data_row.get('results', [])
        results_data.append(result)
        data_row['results'] = results_data
        data_row['presenter'] = row.presenter
        data[tmpl_id] = data_row
    return data


def get_annotations(volume_id, motivation):
    """Return all annotations with a given motivation for a volume."""
    m_query = {"annotations": [{'motivation': motivation}]}
    sql = text('''SELECT result.info->'annotations' AS annotations
               FROM result, project
               WHERE result.project_id = project.id
               AND project.info->'volume_id' @> :volume_id
               AND result.info @> :m_query
               ''')
    results = session.execute(sql, dict(volume_id=json.dumps(volume_id),
                                        m_query=json.dumps(m_query)))
    annotations = []
    for row in results:
        valid_annos = [anno for anno in row.annotations
                       if anno['motivation'] == motivation]
        annotations += valid_annos
    return annotations
