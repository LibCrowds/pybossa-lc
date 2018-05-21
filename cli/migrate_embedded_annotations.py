#!/usr/bin/env python
"""
Export Annotations embedded in the PYBOSSA results info field.

Usage:

export SERVER_NAME='https://backend.libcrowds.com'
export GITHUB_REPO='https://github.com/LibCrowds/libcrowds'
export SPA_SERVER_NAME='https://www.libcrowds.com'

python cli/migrate_embedded_annotations.py
"""

import os
import json
import click
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


def get_category_id():
    """Prompt for a category ID."""
    query = text('''SELECT id, name FROM category''')
    db_results = db.engine.execute(query)
    categories = db_results.fetchall()
    for category in categories:
        print '{0}: {1}'.format(category.id, category.name)
    category_id = click.prompt('Please enter a category ID', type=int)
    if category_id not in [c.id for c in categories]:
        raise ValueError('Invalid choice')
    return category_id


def get_projects(category_id):
    """Get the category's projects."""
    query = text('''SELECT id
                    FROM project
                    WHERE category_id=:category_id''')
    db_results = db.engine.execute(query, category_id=category_id)
    projects = db_results.fetchall()
    print('Updating {} projects'.format(len(projects)))
    return projects

def run():
    with app.app_context():
        container_iri = click.prompt('Please enter a container IRI', type=str)
        start = click.prompt('Start at result ID:', type=int, default=0)
        category_id = get_category_id()
        projects = get_projects(category_id)
        
        i = 0
        for project in projects:

            query = text('''SELECT id, info->>'annotations' AS annotations
                        FROM result, task
                        WHERE (result.info->>'annotations') IS NOT NULL
                        AND result.project_id=:project_id
                        AND result.task_id=task.id
                        AND result.id > :start
                        ''')
            kwargs = dict(project_id=project.id, start=start)
            db_results = db.engine.execute(query, **kwargs).fetchall()
            for row in db_results:
                annotations = json.loads(row.annotations)
                for anno in annotations:
                    if not anno:
                        continue

                format_annotation(row.id, anno)
                old_iri = anno.pop('id')
                slug = old_iri.rstrip('/').split('/')[-1]
                headers = {
                    'Slug': slug
                }
                res = requests.post(container_iri, json=anno, headers=headers)
                out = res.json()
                
                try:
                    new_iri = out['id']
                except Exception as err:
                    print 'Current result ID:', row.id
                    print 'Status code:', res.status_code
                    print 'Request data:', anno
                    print 'Response data:', out.data
                    raise err

                query = text(
                    '''
                    UPDATE task
                    SET info = info - 'parent_annotation_id'
                    || jsonb_build_object('parent_annotation_id', :new_iri)
                    WHERE (info->>'parent_annotation_id') = :old_iri
                    '''
                )
                db.engine.execute(query, new_iri=new_iri, old_iri=old_iri)
                i += 1

            if i % 100 == 0:
                print '{0} Annotations exported'.format(i)

if __name__ == '__main__':
    run()
