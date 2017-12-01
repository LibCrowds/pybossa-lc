# -*- coding: utf8 -*-
"""Test Z39.50 analysis."""

import numpy
import pandas
from mock import patch, call
from factories import TaskFactory, TaskRunFactory, ProjectFactory
from default import Test, with_context, db
from pybossa.repositories import ResultRepository

from pybossa_lc.analysis import z3950


class TestZ3950Analysis(Test):

    def setUp(self):
        super(TestZ3950Analysis, self).setUp()
        self.result_repo = ResultRepository(db)

    @with_context
    def test_empty_results(self):
        """Test that an empty result is updated correctly."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info={
            'control_number': '',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert result.last_version, "last_version should be True"
        assert result.info == {
            'control_number': '',
            'reference': '',
            'comments': ''
        }, "info should be empty values for all keys"

    @with_context
    def test_results_with_deprecated_keys(self):
        """Test that the old Convert-a-Card keys are converted."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info={
            'oclc': '',
            'shelfmark': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert result.info == {
            'control_number': '',
            'reference': '',
            'comments': ''
        }, "keys should be updated to the new names"

    @with_context
    def test_results_with_comments(self):
        """Test that results with comments are updated correctly."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info={
            'control_number': '',
            'reference': '',
            'comments': 'Some comment'
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert not result.last_version, "last_version should be False"
        assert result.info == {
            'control_number': '',
            'reference': '',
            'comments': ''
        }, "info should be empty values for all keys"

    @with_context
    def test_results_with_matching_answers(self):
        """Test that results with matching answers are updated correctly."""
        task = TaskFactory.create(n_answers=3)
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': 'def',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '456',
            'reference': 'abc',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert result.last_version, "last_version should be True"
        assert result.info == {
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        }, "control_number and reference should be populated"

    @with_context
    def test_results_with_non_matching_answers(self):
        """Test results with non-matching answers are updated correctly."""
        task = TaskFactory.create(n_answers=3)
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '456',
            'reference': 'abc',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '789',
            'reference': 'abc',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert not result.last_version, "last_version should be False"
        assert result.info == {
            'control_number': '',
            'reference': '',
            'comments': ''
        }, "info should be empty values for all keys"

    @with_context
    @patch('pybossa_lc.analysis.z3950.analyse', return_value=True)
    def test_all_results_analysed(self, mock_analyse):
        """Test results with non-matching answers are updated correctly."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        calls = [call(r) for r in results]
        z3950.analyse_all(project.id)
        assert mock_analyse.has_calls(calls, any_order=True)
