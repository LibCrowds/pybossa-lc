# -*- coding: utf8 -*-

from factories import CategoryFactory, ProjectFactory, TaskFactory
from pybossa.core import project_repo

from .template import TemplateFixtures


class ContextFixtures(object):

    def create_task(self, n_answers, target='example.com', max_answers=None,
                    rules=None, info=None,
                    anno_collection='http://anno.com/collection'):
        """Create a category, project and tasks."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create()
        tmpl.min_answers = n_answers
        tmpl.max_answers = max_answers or n_answers
        if rules:
            tmpl.rules = rules
        project_info = dict(template_id=tmpl.id)
        category.info['templates'] = [tmpl.to_dict()]
        if anno_collection:
            category.info['annotations'] = dict(results=anno_collection)
        project_repo.update_category(category)
        project = ProjectFactory.create(category=category, info=project_info)
        task_info = dict(target=target)
        if info:
            task_info.update(info)
        return TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
