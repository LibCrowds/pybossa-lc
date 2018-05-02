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
                if 'id' not in anno:  # Add new ID if none
                    anno['id'] = str(uuid.uuid4())
                elif '://' in anno['id']:  # Remove URI based IDs
                    anno['id'] = anno['id'].split('/')[-1]

            result.info['annotations'] = annotations

            new_info = result.info.copy()
            query = text('''UPDATE result
                            SET info=:info
                            WHERE id=:id''')
            db.engine.execute(query, id=result.id,
                              info=json.dumps(new_info))


if __name__ == '__main__':
    run()
