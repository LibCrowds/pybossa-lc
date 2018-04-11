#!/usr/bin/env python
"""
Add id to all annotations.

Usage:
python cli/add_ids_to_annotations.py
"""

import sys
import json
import uuid
import click
from sqlalchemy.sql import text
from pybossa.core import db, create_app

app = create_app(run_as_server=False)


def get_anno_id():
    """Return the anno ID."""
    spa_server_name = app.config.get('SPA_SERVER_NAME')
    anno_uuid = str(uuid.uuid4())
    return '{0}/lc/annotations/{1}'.format(spa_server_name, anno_uuid)


@click.command()
def run():
    with app.app_context():
        # Get all results
        query = text('''SELECT result.id, result.info
                    FROM result
                    WHERE (result.info->>'annotations') IS NOT NULL
                    ''')
        db_results = db.engine.execute(query)
        results = db_results.fetchall()
        for result in results:
            annotations = result.info['annotations']
            for anno in annotations:
                if not anno.get('id'):
                    anno['id'] = get_anno_id()

            result.info['annotations'] = annotations

            new_info = dict(annotations=annotations)
            query = text('''UPDATE result
                            SET info=:info
                            WHERE id=:id''')
            db.engine.execute(query, id=result.id,
                              info=json.dumps(new_info))

if __name__ == '__main__':
    run()
