# -*- coding: utf8 -*-
"""Test Z39.50 analysis."""

import numpy
import pandas
from mock import patch, call
from freezegun import freeze_time
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
    def test_old_info_returned(self):
        """Test that old info from previous analysis module is returned."""
        result_info = {
            'oclc': '123',
            'shelfmark': '456',
            'shelfmark-option': '789',
            'comments': '0'
        }
        old_info = z3950.get_old_info(result_info)
        assert_not_equal(old_info, None)
        assert_dict_equal(old_info, {
            'control_number': '123',
            'reference': '789',
            'comments': '0'
        })

    @with_context
    def test_empty_results(self):
        """Test that an empty result is updated correctly."""
        project = ProjectFactory.create()
        task = TaskFactory.create(n_answers=1, project=project, info={})
        TaskRunFactory.create(task=task, info={
            'control_number': '',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_equal(result.info, {
            'annotations': []
        })

    @with_context
    @freeze_time("19-11-1984")
    @patch("pybossa_lc.analysis.z3950.helpers.create_commenting_anno")
    def test_comment_annotation_created(self, mock_create_comment_anno):
        """Test that a comment annotation is created."""
        mock_create_comment_anno.return_value = {}
        project = ProjectFactory.create()
        comment = 'Some comment'
        target = "example.com"
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=1, project=project, info=task_info)
        TaskRunFactory.create(task=task, info={
            'control_number': '',
            'reference': '',
            'comments': comment
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, False)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_comment_anno.assert_called_once_with(target, comment)

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    def test_results_with_matching_answers(self, mock_create_desc_anno):
        """Test that results with matching answers are updated correctly."""
        mock_create_desc_anno.return_value = {}
        project = ProjectFactory.create()
        n_answers = 3
        target = "example.com"
        ctrl_n = 'foo'
        ref = 'bar'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'control_number': ctrl_n,
                'reference': ref,
                'comments': ''
            })

        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_equal(len(result.info['annotations']), 2)
        call_args_list = mock_create_desc_anno.call_args_list
        assert_equal(len(call_args_list), 2)
        assert call(target, ref, 'reference') in call_args_list
        assert call(target, ctrl_n, 'control_number') in call_args_list

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    def test_results_with_deprecated_keys(self, mock_create_desc_anno):
        """Test that deprecated keys are converted."""
        mock_create_desc_anno.return_value = {}
        project = ProjectFactory.create()
        n_answers = 3
        target = "example.com"
        ctrl_n = 'foo'
        ref = 'bar'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'oclc': ctrl_n,
                'shelfmark': ref,
                'comments': ''
            })

        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_equal(len(result.info['annotations']), 2)
        call_args_list = mock_create_desc_anno.call_args_list
        assert_equal(len(call_args_list), 2)
        assert call(target, ref, 'reference') in call_args_list
        assert call(target, ctrl_n, 'control_number') in call_args_list

    @with_context
    def test_results_with_non_matching_answers(self):
        """Test results with non-matching answers are updated correctly."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info={})
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'control_number': 'ctrl{}'.format(i),
                'reference': 'ref{}'.format(i),
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, False)
        assert_equal(result.info['annotations'], [])

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
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    def test_references_are_normalised(self, mock_create_desc_anno):
        """Test references are normalised according to set analysis rules."""
        mock_create_desc_anno.return_value = {}
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl['rules'] = dict(case='title', whitespace='full_stop',
                             trim_punctuation=True)
        UserFactory.create(info=dict(templates=[tmpl]))
        project = ProjectFactory.create(info=dict(template_id=tmpl['id']))
        target = "example.com"
        ctrl_n = 'foo'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=3, project=project, info=task_info)
        TaskRunFactory.create(task=task, info={
            'control_number': ctrl_n,
            'reference': 'OR 123  456.',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': ctrl_n,
            'reference': 'Or.123.456. ',
            'comments': ''
        })
        TaskRunFactory.create(task=task, info={
            'control_number': ctrl_n,
            'reference': 'or 123 456',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_equal(len(result.info['annotations']), 2)
        call_args_list = mock_create_desc_anno.call_args_list
        assert_equal(len(call_args_list), 2)
        assert call(target, 'Or.123.456', 'reference') in call_args_list
        assert call(target, ctrl_n, 'control_number') in call_args_list

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    def test_old_unverified_key_cleared(self, mock_create_desc_anno):
        """Test that the old Unverified key is cleared."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info={})
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'control_number': 'ctrl{}'.format(i),
                'reference': 'ref{}'.format(i),
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = 'Unverified'
        self.result_repo.update(result)
        z3950.analyse(result.id)
        assert_equal(result.last_version, False)
        assert_equal(result.info['annotations'], [])

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    @patch("pybossa_lc.analysis.z3950.helpers.create_commenting_anno")
    def test_results_from_old_module_stored(self, mock_create_comment_anno,
                                            mock_create_desc_anno):
        """Test that any results from the old analysis module are stored."""
        mock_create_desc_anno.return_value = {}
        mock_create_comment_anno.return_value = {}
        project = ProjectFactory.create()
        n_answers = 3
        target = "example.com"
        ctrl_n = 'foo'
        ref = 'bar'
        comment = 'baz'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        answer = {
            'oclc': '123',
            'shelfmark': 'foo',
            'comments': 'bar'
        }
        TaskRunFactory.create_batch(n_answers, task=task, info=answer)

        # Ensure that any verified answer from the old module is not replaced
        verified_answer = {
            'oclc-option': ctrl_n,
            'oclc': '',
            'shelfmark-option': ref,
            'shelfmark': '',
            'comments-option': comment,
            'comments': 'some comment'
        }

        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = verified_answer
        self.result_repo.update(result)
        z3950.analyse(result.id, _all=True)
        assert_equal(result.last_version, True)
        assert_equal(len(result.info['annotations']), 3)
        desc_call_args_list = mock_create_desc_anno.call_args_list
        comment_call_args_list = mock_create_comment_anno.call_args_list
        assert_equal(len(desc_call_args_list), 2)
        assert (
            call(target, ref, 'reference', modified=True)
            in desc_call_args_list
        )
        assert (
            call(target, ctrl_n, 'control_number', modified=True)
            in desc_call_args_list
        )
        assert call(target, comment) in comment_call_args_list

    @with_context
    def test_result_not_auto_updated_if_info_field_already_populated(self):
        """Test that a result is not updated if the info field is not empty."""
        project = ProjectFactory.create()
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info={})
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '123',
            'reference': 'abc',
            'comments': ''
        })
        original_answer = dict(annotations=[])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = original_answer
        self.result_repo.update(result)
        z3950.analyse(result.id)
        assert_equal(result.last_version, True)
        assert_dict_equal(result.info, original_answer)

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_commenting_anno")
    def test_result_updated_if_all_is_true(self, mock_create_comment_anno):
        """Test that a result is updated if info populated and _all=True."""
        mock_create_comment_anno.return_value = True
        project = ProjectFactory.create()
        n_answers = 1
        target = "example.com"
        comment = 'foo'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '',
            'reference': '',
            'comments': comment
        })
        original_answer = dict(annotations=[])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = original_answer
        self.result_repo.update(result)
        z3950.analyse(result.id, _all=True)
        assert_equal(result.last_version, False)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_comment_anno.assert_called_once_with(target, comment)

    @with_context
    @patch("pybossa_lc.analysis.z3950.helpers.create_describing_anno")
    def test_modified_annotations_are_not_updated(self, mock_create_desc_anno):
        """Test that a manually modified result is not updated."""
        mock_create_desc_anno.return_value = {}
        project = ProjectFactory.create()
        n_answers = 3
        target = "example.com"
        tag = 'control_number'
        ctrl_n = 'foo'
        ref = 'bar'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '123',
            'reference': ref,
            'comments': ''
        })
        original_answer = dict(annotations=[
            {
                "motivation": "describing",
                "body": [
                    {
                        "type": "TextualBody",
                        "purpose": "describing",
                        "value": ctrl_n,
                        "format": "text/plain",
                        "modified": "2015-01-29T09:00:00Z"
                    },
                    {
                        "type": "TextualBody",
                        "purpose": "tagging",
                        "value": tag
                    }
                ]
            }
        ])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = original_answer
        self.result_repo.update(result)
        z3950.analyse(result.id, _all=True)
        assert_equal(result.last_version, True)
        assert_equal(len(result.info['annotations']), 2)
        mock_create_desc_anno.assert_called_once_with(target, ref, 'reference')
