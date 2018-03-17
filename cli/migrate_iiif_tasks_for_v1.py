#!/usr/bin/env python
"""
Migrate IIIF tasks from pre LibCrowds v1.0.0 configuration.

Usage:
python cli/migrate_iiif_tasks_for_v1.py
"""

import json
import click
from sqlalchemy.sql import text
from pybossa.core import db, create_app

app = create_app(run_as_server=False)


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
            print project



            # Get the project's results
            query = text('''SELECT task.id, task.info
                         FROM task
                         WHERE task.project_id=:project_id
                         ''')
            db_results = db.engine.execute(query, project_id=project.id)
            tasks = db_results.fetchall()
            for task in tasks:
                info = task.info

                # Rename task.info.info > task.info.manifest
                if 'info' in task.info:
                    task.info['manifest'] = task.info.pop('info')

                # Rename task.info.shareUrl > task.info.link
                if 'shareUrl' in task.info:
                    task.info['link'] = task.info.pop('shareUrl')

                # Drop fields mostly now handled via templates
                task.info.pop('help', None)
                task.info.pop('objective', None)
                task.info.pop('guidance', None)
                task.info.pop('form', None)
                task.info.pop('classification', None)
                task.info.pop('mode', None)
                task.info.pop('thumbnailUrl', None)

                # Convert higlights and bounds into target FragmentSelector
                if 'highlights' in task.info:
                    rect = task.info.pop('highlights')[0]
                    selector = '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                              rect['y'],
                                                              rect['width'],
                                                              rect['height'])
                    task.info.pop('bounds', None)
                    task.info['target'] = {
                        'source': task.info['target'],
                        'selector': {
                            'conformsTo': 'http://www.w3.org/TR/media-frags/',
                            'type': 'FragmentSelector',
                            'value': selector
                        }
                    }

                new_info = json.dumps(task.info)
                query = text('''UPDATE task
                             SET info=:info
                             WHERE id=:id''')
                db.engine.execute(query, id=task.id, info=new_info)


if __name__ == '__main__':
    run()
