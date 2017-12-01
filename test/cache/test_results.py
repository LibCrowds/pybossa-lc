# -*- coding: utf8 -*-
"""Test results cache."""

from default import Test, with_context, db
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository

from pybossa_lc.cache import results as results_cache


class TestResultsCache(Test):

    def setUp(self):
        super(TestResultsCache, self).setUp()
        self.result_repo = ResultRepository(db)

    @with_context
    def test_empty_results(self):
        """Test the correct functions are triggered for the Z39.50 endpoint."""
        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        data = results_cache.empty_results()
        assert data == [{
            'short_name': project.short_name,
            'n_empty_results': 1
        }]
