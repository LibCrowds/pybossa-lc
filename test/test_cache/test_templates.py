# -*- coding: utf8 -*-
"""Test templates cache."""

import datetime
from default import Test, with_context, db
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository

from pybossa_lc.cache import results as results_cache


class TestResultsCache(Test):

    def setUp(self):
        super(TestResultsCache, self).setUp()
        self.result_repo = ResultRepository(db)

    def convert_time(self, timestamp_str):
        pattern = "%Y-%m-%dT%H:%M:%S.%f"
        return datetime.datetime.strptime(timestamp_str, pattern)

    @with_context
    def test_empty_results_under_a_day_old_are_not_returned(self):
        """Test that empty results under a day old are not returned."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.created = datetime.datetime.utcnow()
        self.result_repo.update(result)
        data = results_cache.empty_results()
        assert data == []