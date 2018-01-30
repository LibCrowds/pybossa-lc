# -*- coding: utf8 -*-
"""Test Z39.50 analysis."""

import numpy
import pandas
from mock import patch, call
from factories import TaskFactory, TaskRunFactory, ProjectFactory
from factories import CategoryFactory, UserFactory
from default import Test, with_context, db
from pybossa.repositories import ResultRepository
from nose.tools import *

from ..fixtures import TemplateFixtures
from pybossa_lc.analysis import z3950


class TestZ3950Analysis(Test):

    def setUp(self):
        super(TestZ3950Analysis, self).setUp()
        self.result_repo = ResultRepository(db)

    @with_context
    def test_empty_results(self):
        """Test that an empty result is updated correctly."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=1, project=project)
        TaskRunFactory.create(task=task, info={
            'control_number': '',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, {
            'control_number': '',
            'reference': '',
            'comments': ''
        })

    @with_context
    def test_results_with_deprecated_keys(self):
        """Test that the old Convert-a-Card keys are converted."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=1, project=project)
        TaskRunFactory.create(task=task, info={
            'oclc': '',
            'shelfmark': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_dict_equal(result.info, {
            'control_number': '',
            'reference': '',
            'comments': ''
        })

    @with_context
    def test_results_with_comments(self):
        """Test that results with comments are updated correctly."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=3, project=project)
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': '456',
            'comments': 'Some comment'
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': '456',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': '456',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, False)
        assert_dict_equal(result.info, {
            'control_number': '',
            'reference': '',
            'comments': ''
        })

    @with_context
    def test_results_with_matching_answers(self):
        """Test that results with matching answers are updated correctly."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=3, project=project)
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
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, {
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        })

    @with_context
    def test_results_with_non_matching_answers(self):
        """Test results with non-matching answers are updated correctly."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=3, project=project)
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
        assert_equal(result.last_version, False)
        assert_dict_equal(result.info, {
            'control_number': '',
            'reference': '',
            'comments': ''
        })

    @with_context
    @patch('pybossa_lc.analysis.z3950.analyse', return_value=True)
    def test_all_results_analysed(self, mock_analyse):
        """Test all Z39.50 results analysed."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        calls = [call(r.id) for r in results]
        z3950.analyse_all(project.id)
        assert mock_analyse.has_calls(calls, any_order=True)

    @with_context
    @patch('pybossa_lc.analysis.z3950.analyse', return_value=True)
    def test_empty_results_analysed(self, mock_analyse):
        """Test empty Z39.50 results analysed."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        results[0].info = dict(foo='bar')
        self.result_repo.update(results[0])
        z3950.analyse_empty(project.id)
        mock_analyse.assert_called_once_with(results[1].id)

    @with_context
    def test_references_are_normalised(self):
        """Test references are normalised according to set analysis rules."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl['rules'] = dict(case='title', whitespace='full_stop',
                             trim_punctuation=True)
        UserFactory.create(info=dict(templates=[tmpl]))
        project = ProjectFactory.create(info=dict(template_id=tmpl['id']))
        task = TaskFactory.create(n_answers=3, project=project)
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': 'OR 123  456.',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '123',
            'reference': 'Or.123.456. ',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': '456',
            'reference': 'or 123 456',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, {
            'control_number': '123',
            'reference': 'Or.123.456',
            'comments': ''
        })

    @with_context
    def test_result_not_auto_updated_if_info_field_already_populated(self):
        """Test that a result is not updated if the info field is not empty."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        })
        original_answer = {
            'control_number': '789',
            'reference': 'foo',
            'comments': 'bar'
        }
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = original_answer
        self.result_repo.update(result)
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, original_answer)

    @with_context
    def test_old_unverified_key_cleared(self):
        """Test that the old Unverified key is cleared."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project)
        answer = {
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        }
        TaskRunFactory.create_batch(n_answers, task=task, info=answer)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = 'Unverified'
        self.result_repo.update(result)
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, answer)

    @with_context
    def test_bad_headers_from_old_module_fixed(self):
        """Test that bad headers from the old analysis module are fixed."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project)
        answer = {
            'oclc': '123',
            'shelfmark': 'foo',
            'comments': 'bar'
        }
        # Also making sure that the verified answer is not replaced
        verified_answer = {
            'oclc-option': '789',
            'oclc': '',
            'shelfmark-option': 'baz',
            'shelfmark': '',
            'comments-option': 'some comment',
            'comments': 'some comment'
        }
        TaskRunFactory.create_batch(n_answers, task=task, info=answer)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = verified_answer
        self.result_repo.update(result)
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, {
            'control_number': '789',
            'reference': 'baz',
            'comments': 'some comment'
        })
