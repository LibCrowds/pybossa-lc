# -*- coding: utf8 -*-
"""Test Z39.50 analyst."""

import pandas
from nose.tools import *
from mock import patch, call, MagicMock
from default import Test, with_context, db, flask_app
from factories import TaskRunFactory, UserFactory
from pybossa.repositories import ResultRepository, TaskRepository
from flask import url_for

from ..fixtures.context import ContextFixtures
from ..fixtures.template import TemplateFixtures
from pybossa_lc.analysis.z3950 import Z3950Analyst


class TestZ3950Analyst(Test):

    def setUp(self):
        super(TestZ3950Analyst, self).setUp()
        self.ctx = ContextFixtures()
        self.z3950_analyst = Z3950Analyst()
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)
        self.data = {
            'user_id': [1],
            'control_number': ['123'],
            'reference': ['abc'],
            'foo': ['bar'],
            'comments': ['Some comment']
        }

    def test_get_comments(self):
        """Test Z3950 comments are returned."""
        task_run_df = pandas.DataFrame(self.data)
        comments = self.z3950_analyst.get_comments(task_run_df)
        expected = [(self.data['user_id'][i], self.data['comments'][i])
                    for i in range(len(self.data['user_id']))]
        assert_equal(comments, expected)

    def test_get_tags(self):
        """Test Z3950 tags are returned."""
        task_run_df = pandas.DataFrame(self.data)
        tags = self.z3950_analyst.get_tags(task_run_df)
        assert_dict_equal(tags, {})

    def test_get_transcriptions_df(self):
        """Test Z3950 transcriptions are returned."""
        task_run_df = pandas.DataFrame(self.data)
        df = self.z3950_analyst.get_transcriptions_df(task_run_df)
        assert_dict_equal(df.to_dict(), {
            'control_number': dict(enumerate(self.data['control_number'])),
            'reference': dict(enumerate(self.data['reference']))
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_analysis_with_no_transcriptions(self, mock_client):
        """Test Z3950 analysis with no transcriptions."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_analysis_with_no_transcriptions_and_old_keys(self, mock_client):
        """Test Z3950 analysis with no transcriptions and old keys."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'oclc': '',
            'shelfmark': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_analysis_with_no_reference(self, mock_client):
        """Test Z3950 analysis with no reference."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': 'foo',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_analysis_with_no_control_number(self, mock_client):
        """Test Z3950 analysis with no control number."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '',
            'reference': 'foo',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_comment_annotation_created(self, mock_client):
        """Test Z3950 comment annotations are created."""
        n_answers = 1
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target,
                                    anno_collection=anno_collection)
        user = UserFactory()
        value = 'foo'
        TaskRunFactory.create_batch(n_answers, user=user, task=task, info={
            'control_number': '',
            'reference': '',
            'comments': value
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
            'motivation': 'commenting',
            'type': 'Annotation',
            'creator': {
                'id': url_for('api.api_user', oid=user.id),
                'type': 'Person',
                'name': user.fullname,
                'nickname': user.name
            },
            'generator': [
                {
                    "id": flask_app.config.get('GITHUB_REPO'),
                    "type": "Software",
                    "name": "LibCrowds",
                    "homepage": flask_app.config.get('SPA_SERVER_NAME')
                },
                {
                    "id": url_for('api.api_result', oid=result.id),
                    "type": "Software"
                }
            ],
            'body': {
                'type': 'TextualBody',
                'purpose': 'commenting',
                'value': value,
                'format': 'text/plain'
            },
            'target': target
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_transcriptions_are_normalised(self, mock_client):
        """Test Z3950 transcriptions are normalised according to set rules."""
        n_answers = 1
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        rules = dict(case='title', whitespace='full_stop',
                     trim_punctuation=True)
        task = self.ctx.create_task(n_answers, target, rules=rules,
                                    anno_collection=anno_collection)
        control_number = 'foo'
        references = ['OR 123  456.', 'Or.123.456. ', 'or 123 456']
        for value in references:
            TaskRunFactory.create(task=task, info={
                'reference': value,
                'control_number': control_number,
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.call_args_list, [
            call(anno_collection, {
                'motivation': 'describing',
                'type': 'Annotation',
                'generator': [
                    {
                        "id": flask_app.config.get('GITHUB_REPO'),
                        "type": "Software",
                        "name": "LibCrowds",
                        "homepage": flask_app.config.get('SPA_SERVER_NAME')
                    },
                    {
                        "id": url_for('api.api_result', oid=result.id),
                        "type": "Software"
                    }
                ],
                'body': [
                    {
                        'type': 'TextualBody',
                        'purpose': 'describing',
                        'value': control_number.capitalize(),
                        'format': 'text/plain'
                    },
                    {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': 'control_number'
                    }
                ],
                'target': target
            }),
            call(anno_collection, {
                'motivation': 'describing',
                'type': 'Annotation',
                'generator': [
                    {
                        "id": flask_app.config.get('GITHUB_REPO'),
                        "type": "Software",
                        "name": "LibCrowds",
                        "homepage": flask_app.config.get('SPA_SERVER_NAME')
                    },
                    {
                        "id": url_for('api.api_result', oid=result.id),
                        "type": "Software"
                    }
                ],
                'body': [
                    {
                        'type': 'TextualBody',
                        'purpose': 'describing',
                        'value': 'Or.123.456',
                        'format': 'text/plain'
                    },
                    {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': 'reference'
                    }
                ],
                'target': target
            })
        ])

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_with_matching_transcriptions(self, mock_client):
        """Test Z3950 results with matching transcriptions."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        reference = 'foo'
        control_number = 'bar'
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'reference': reference,
            'control_number': control_number,
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        func = mock_client.create_annotation
        assert_equal(mock_client.create_annotation.call_args_list, [
            call(anno_collection, {
                'motivation': 'describing',
                'type': 'Annotation',
                'generator': [
                    {
                        "id": flask_app.config.get('GITHUB_REPO'),
                        "type": "Software",
                        "name": "LibCrowds",
                        "homepage": flask_app.config.get('SPA_SERVER_NAME')
                    },
                    {
                        "id": url_for('api.api_result', oid=result.id),
                        "type": "Software"
                    }
                ],
                'body': [
                    {
                        'type': 'TextualBody',
                        'purpose': 'describing',
                        'value': control_number,
                        'format': 'text/plain'
                    },
                    {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': 'control_number'
                    }
                ],
                'target': target
            }),
            call(anno_collection, {
                'motivation': 'describing',
                'type': 'Annotation',
                'generator': [
                    {
                        "id": flask_app.config.get('GITHUB_REPO'),
                        "type": "Software",
                        "name": "LibCrowds",
                        "homepage": flask_app.config.get('SPA_SERVER_NAME')
                    },
                    {
                        "id": url_for('api.api_result', oid=result.id),
                        "type": "Software"
                    }
                ],
                'body': [
                    {
                        'type': 'TextualBody',
                        'purpose': 'describing',
                        'value': reference,
                        'format': 'text/plain'
                    },
                    {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': 'reference'
                    }
                ],
                'target': target
            })
        ])

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_increased_when_not_max(self, mock_client):
        """Test Z3950 task redundancy is updated when max not reached."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target, max_answers=4)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'reference': i,
                'control_number': i,
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers + 1)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_when_max(self, mock_client):
        """Test Z3950 task redundancy is not updated when max is reached."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target, max_answers=3)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'reference': i,
                'control_number': i,
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_for_comments(self, mock_client):
        """Test Z3950 task redundancy is not updated for comments."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'reference': 'foo',
                'control_number': 'bar',
                'comments': i
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_when_no_values(self, mock_client):
        """Test Z3950 task redundancy is not updated when no values."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                'reference': '',
                'control_number': '',
                'comments': ''
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_search = MagicMock()
        fake_search.return_value = []
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_old_annotations_deleted(self, mock_client):
        """Test Z3950 old Annotations deleted."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'reference': '',
            'control_number': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_annos = [
            {
                'id': 'baz'
            },
            {
                'id': 'qux'
            }
        ]
        fake_search = MagicMock()
        fake_search.return_value = fake_annos
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id, analyse_full=True)
        mock_client.delete_batch.assert_called_once_with(fake_annos)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_results_with_annotations_not_analysed(self, mock_client):
        """Test results with Annotations already not analysed by default."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'reference': 'foo',
            'control_number': 'bar',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_annos = [
            {
                'id': 'baz'
            },
            {
                'id': 'qux'
            }
        ]
        fake_search = MagicMock()
        fake_search.return_value = fake_annos
        mock_client.search_annotations = fake_search
        self.z3950_analyst.analyse(result.id)
        assert_equal(mock_client.delete_batch.called, False)
