#!/usr/bin/env python
"""
Export Annotations embedded in the PYBOSSA results info field.

Usage:

export SERVER_NAME='https://backend.libcrowds.com'
export GITHUB_REPO='https://github.com/LibCrowds/libcrowds'
export SPA_SERVER_NAME='https://www.libcrowds.com'
export CONTAINER_IRI='https://annotations.libcrowds.com/my-container/'

python cli/migrate_embedded_annotations.py
"""

import os
import json
import requests
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
        i = 0
        for row in db_results:
            i += 1
            annotations = json.loads(row.annotations)
            for anno in annotations:
                if not anno:
                    continue

                format_annotation(row.id, anno)
                endpoint = os.environ['CONTAINER_IRI']
                data = json.dumps(anno)
                old_iri = anno.pop('id')
                slug = old_iri.rstrip('/').split('/')[-1]
                headers = {
                    'Slug': slug
                }
                res = requests.post(endpoint, data=data, headers=headers)
                out = res.json()
                new_iri = out['id']

                query = text(
                    '''
                    UPDATE task
                    SET info = info - 'parent_annotation_id'
                    || jsonb_build_object('parent_annotation_id', :new_iri)
                    WHERE (info->>'parent_annotation_id') = :old_iri
                    '''
                )
                db.engine.execute(query, new_iri=new_iri, old_iri=old_iri)

            if i % 1000 == 0:
                print '{0} Annotations exported'.format(i)

if __name__ == '__main__':
    run()
