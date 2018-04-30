# -*- coding: utf8 -*-
"""Test background jobs."""

from nose.tools import *
from default import Test, with_context
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory

from pybossa_lc.cache import results as results_cache


class TestResultsCache(Test):

    @with_context
    def test_categories_returned_with_unanalysed_count(self):
        """Test all categories are with unanalysed results count."""
        category1 = CategoryFactory()
        category2 = CategoryFactory()
        project = ProjectFactory.create(category=category1)
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)

        unanalysed_categories = results_cache.get_unanalysed_by_category()
        assert_equal(unanalysed_categories, [
            {
                'category_id': category1.id,
                'category_name': category1.name,
                'n_unanalysed': 1
            }
        ])
