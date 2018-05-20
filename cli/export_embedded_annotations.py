#!/usr/bin/env python
"""
Export Annotations embedded in the PYBOSSA results info field.

Usage:
python cli/export_embedded_annotations.py
"""

import json
from sqlalchemy.sql import text
from pybossa.core import db, create_app

app = create_app(run_as_server=False)

def run():
    with app.app_context():
        query = text('''SELECT result.info->>'annotations' AS annotations
                     FROM result
                     WHERE (result.info->>'annotations') IS NOT NULL
                     ''')
        db_results = db.engine.execute(query).fetchall()
        with open('out.json', 'wb') as out_file:
            out_file.write('[')
            first = True
            for row in db_results:
                annotations = json.loads(row.annotations)
                for anno in annotations:
                    if not anno:
                        continue
                    if not first:
                        out_file.write(', ')
                    json.dump(anno, out_file, indent=2)
                    first = False
            out_file.write(']')

if __name__ == '__main__':
    run()
