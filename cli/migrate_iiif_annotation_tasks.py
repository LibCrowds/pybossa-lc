#!/usr/bin/env python
"""
Migrate tasks from non-template based IIIF Annotation projects.

Usage:
python cli/migrate_iiif_annotation_tasks.py
"""

import sys
import json
import click
from datetime import datetime
from sqlalchemy.sql import text
from pybossa.core import db, create_app

app = create_app(run_as_server=False)


def get_xsd_datetime():
    """Return timestamp expressed in the UTC xsd:datetime format."""
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_anno_base(motivation):
    """Return the base fo ra new Web Annotation."""
    ts_now = get_xsd_datetime()
    spa_server_name = app.config.get('SPA_SERVER_NAME')
    github_repo = app.config.get('GITHUB_REPO')
    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "motivation": motivation,
        "created": ts_now,
        "generated": ts_now,
        "generator": {
            "id": github_repo,
            "type": "Software",
            "name": "LibCrowds",
            "homepage": spa_server_name
        }
    }


def create_commenting_anno(target, value):
    """Create a Web Annotation with the commenting motivation."""
    anno = get_anno_base('commenting')
    anno['target'] = target
    anno['body'] = {
        "type": "TextualBody",
        "value": value,
        "purpose": "commenting",
        "format": "text/plain"
    }
    return anno


def create_desc_anno(target, value, tag):
    """Create a Web Annotation with the describing motivation."""
    anno = get_anno_base('describing')
    anno['target'] = target
    anno['body'] = [
        {
            "type": "TextualBody",
            "purpose": "describing",
            "value": value,
            "format": "text/plain",
            "modified": get_xsd_datetime()
        },
        {
            "type": "TextualBody",
            "purpose": "tagging",
            "value": tag
        }
    ]
    return anno


@click.command()
def run():
    with app.app_context():

        # Prompt for a category ID
        query = text('''SELECT id, name FROM category''')
        db_results = db.engine.execute(query)
        categories = db_results.fetchall()
        for category in categories:
            print '{0}: {1}'.format(category.id, category.name)
        category_id = click.prompt('Please enter a category ID', type=int)
        if category_id not in [c.id for c in categories]:
            print 'Invalid choice'
            return

        # Get the category's projects
        query = text('''SELECT id
                     FROM project
                     WHERE category_id=:category_id''')
        db_results = db.engine.execute(query, category_id=category_id)
        projects = db_results.fetchall()
        print('Updating {} projects'.format(len(projects)))
        for project in projects:

            # Get the project's results
            query = text('''SELECT result.id, result.info,
                         task.info AS task_info
                         FROM result, task
                         WHERE result.project_id=:project_id
                         AND result.task_id=task.id
                         AND (result.info->>'annotations') IS NULL
                         ''')
            db_results = db.engine.execute(query, project_id=project.id)
            results = db_results.fetchall()
            for result in results:

                # Migrate
                target = result.task_info['link']
                old_keys = ['oclc', 'shelfmark', 'oclc-option',
                            'shelfmark-option', 'comments-option']
                info = None
                if result.info and any(key in result.info for key in old_keys):

                    def rpl_key(key, new_key):
                        old_val = result.info.get(key)
                        old_analysed = result.info.get('{}-option'.format(key))
                        new_val = result.info.get(new_key)
                        return (old_analysed if old_analysed
                                else new_val if new_val
                                else old_val)

                    info = {
                        'control_number': rpl_key('oclc', 'control_number'),
                        'reference': rpl_key('shelfmark', 'reference'),
                        'comments': rpl_key('comments', 'comments'),
                    }

                if info:
                    annotations = []
                    if info['comments']:
                        anno = create_commenting_anno(target, info['comments'])
                        annotations.append(anno)

                    if info['control_number'] and info['reference']:
                        ctrl_anno = create_desc_anno(target,
                                                     info['control_number'],
                                                     'control_number')
                        ref_anno = create_desc_anno(target,
                                                    info['reference'],
                                                    'reference')
                        annotations.append(ctrl_anno)
                        annotations.append(ref_anno)

                    new_info = dict(annotations=annotations)
                    query = text('''UPDATE result
                                    SET info=:info
                                    WHERE id=:id''')
                    db.engine.execute(query, id=result.id,
                                      info=json.dumps(new_info))


if __name__ == '__main__':
    run()
