#!/usr/bin/env python
"""
Export Annotations embedded in the PYBOSSA results info field.

Usage:

export SERVER_NAME='https://backend.libcrowds.com'
export GITHUB_REPO='https://github.com/LibCrowds/libcrowds'
export SPA_SERVER_NAME='https://www.libcrowds.com'

python cli/export_embedded_annotations.py
"""

import os
import json
from flask import url_for
from sqlalchemy.sql import text
from pybossa.core import db, create_app


app = create_app(run_as_server=False)


def format_annotation(result_id, anno):
    anno.pop('@context', None)
    anno.pop('generated', None)
    anno['generator'] = [
        {
            'id': os.environ['GITHUB_REPO'],
            'type': "Software",
            'name': "LibCrowds",
            'homepage': os.environ['SPA_SERVER_NAME']
        },
        {
            'id': '{0}/api/result/{1}'.format( os.environ['SERVER_NAME'],
                                              result_id),
            'type': 'Software'
        }
    ]


def run():
    with app.app_context():
        query = text('''SELECT id, info->>'annotations' AS annotations
                     FROM result
                     WHERE (result.info->>'annotations') IS NOT NULL
                     LIMIT 100
                     ''')
        db_results = db.engine.execute(query).fetchall()
        with open('out.json', 'wb') as out_file:
            out_file.write('[')
            i = 0
            for row in db_results:
                annotations = json.loads(row.annotations)
                for anno in annotations:
                    if not anno:
                        continue
                    format_annotation(row.id, anno)
                    if i:
                        out_file.write(', ')
                    json.dump(anno, out_file, indent=2)
                    i += 1
            out_file.write(']')
        print '{0} Annotations exported'.format(i)

if __name__ == '__main__':
    run()
