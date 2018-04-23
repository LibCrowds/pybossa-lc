#!/usr/bin/env python
"""
Add partOf attribute to all child annotations.

Note that this relies on all annotations having an id attribute.

Usage:
python cli/add_partof_to_child_annotations.py
"""

import re
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
        print('------------------------------------------')

        for project in projects:
            # Get all child tasks
            query = text('''SELECT task.id, task.info
                        FROM task, project
                        WHERE project.id = :project_id
                        AND task.project_id = project.id
                        AND (task.info->>'parent_task_id') IS NOT NULL
                        ''')
            params = dict(project_id=project.id)
            db_results = db.engine.execute(query, params)
            child_tasks = db_results.fetchall()
            print('Updating {} tasks for project {}'.format(len(child_tasks),
                                                            project.id))

            for child_task in child_tasks:
                parent_task_id = child_task.info['parent_task_id']

                # Get the parent result
                query = text('''SELECT result.id, result.info
                             FROM result, task
                             WHERE task.id = result.task_id
                             AND task.id = :parent_task_id
                             AND result.last_version = True
                             ''')
                params = dict(parent_task_id=parent_task_id)
                db_results = db.engine.execute(query, params)
                results = db_results.fetchall()
                assert len(results) == 1

                parent_result = results[0]
                parent_annos = parent_result.info['annotations']

                # Match parent annotation to child target
                if isinstance(child_task.info['target'], dict):
                    # Strip .0 from child annotations so that they match
                    # These were left over from a previous transformation
                    sel_value = child_task.info['target']['selector']['value']
                    new_value = re.sub(r'\.0', '', sel_value)
                    child_task.info['target']['selector']['value'] = new_value

                parent_anno = [a for a in parent_annos
                               if a['target'] == child_task.info['target']][0]

                child_task.info['parent_annotation_id'] = parent_anno['id']

                # Update child task
                new_info = json.dumps(child_task.info)
                query = text('''UPDATE task
                                SET info=:info
                                WHERE id=:id''')
                db.engine.execute(query, id=child_task.id, info=new_info)

                # Update child annotations
                query = text('''SELECT result.id, result.info
                             FROM result, task
                             WHERE task.id = result.task_id
                             AND (result.info->>'annotations') IS NOT NULL
                             AND task.id = :child_task_id
                             AND result.last_version = True
                             ''')
                params = dict(child_task_id=child_task.id)
                db_results = db.engine.execute(query, params)
                results = db_results.fetchall()
                if not results:
                    continue

                assert len(results) == 1

                child_result = results[0]
                child_annos = child_result.info['annotations']

                for child_anno in child_annos:
                    child_anno['partOf'] = parent_anno['id']

                new_info = json.dumps(child_result.info)
                query = text('''UPDATE result
                                SET info=:info
                                WHERE id=:id''')
                db.engine.execute(query, id=child_result.id, info=new_info)


if __name__ == '__main__':
    run()
