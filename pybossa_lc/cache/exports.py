# -*- coding: utf8 -*-
"""Export formats cache module."""

import json
from sqlalchemy import text
from pybossa.core import db


session = db.slave_session


def get_by_id(export_fmt_id):
    """Return an export format by ID."""
    search_str = json.dumps([{'id': export_fmt_id}])
    sql = text('''SELECT (info->>'export_formats') AS formats
               FROM category
               WHERE (info->>'export_formats')::jsonb @> :search_str''')
    results = session.execute(sql, dict(search_str=search_str))
    for row in results:
        export_formats = json.loads(row.formats)
        return [fmt for fmt in export_formats if fmt['id'] == export_fmt_id][0]
    return None


def get_results_by_tmpls_and_volume(template_ids, volume_id):
    """Return a dict of results against template IDs for a volume."""
    sql = text('''SELECT result.info AS result_info,
               project.info AS project_info
               FROM result, project
               WHERE result.project_id = project.id
               AND project.info->'volume_id' @> :volume_id
               AND project.info->>'template_id' IN :template_ids
               ''')
    results = session.execute(sql, dict(volume_id=json.dumps(volume_id),
                                        template_ids=tuple(template_ids)))
    data = []
    for row in results:
        export_row = dict(result_info=row.result_info,
                          project_info=row.project_info)
        data.append(export_row)
    return data
