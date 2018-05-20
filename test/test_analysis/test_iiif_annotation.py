# -*- coding: utf8 -*-
"""Test IIIF Annotation analyst."""

import pandas
from mock import patch, call, MagicMock
from nose.tools import *
from default import Test, with_context, flask_app, db
from flask import url_for
from factories import UserFactory, TaskRunFactory
from pybossa.repositories import ResultRepository, TaskRepository

from ..fixtures.context import ContextFixtures
from pybossa_lc.analysis.iiif_annotation import IIIFAnnotationAnalyst


class TestIIIFAnnotationAnalyst(Test):

    def setUp(self):
        super(TestIIIFAnnotationAnalyst, self).setUp()
        self.ctx = ContextFixtures()
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)
        self.iiif_analyst = IIIFAnnotationAnalyst()
        self.comments = ['Some comment']
        self.tags = {
            'foo': [
                dict(x=100, y=100, w=100, h=100),
                dict(x=200, y=200, w=200, h=200)
            ],
            'bar': [
                dict(x=300, y=300, w=300, h=300)
            ]
        }
        transcription_data = {
            'foo': ['bar', 'baz'],
            'qux': ['quux', 'quuz']
        }
        self.transcriptions_df = pandas.DataFrame(transcription_data)

        self.comment_annos = []
        for comment in self.comments:
            self.comment_annos.append({
                'motivation': 'commenting',
                'body': {
                    'type': 'TextualBody',
                    'value': comment,
                    'purpose': 'commenting',
                    'format': 'text/plain'
                },
                'target': 'example.com'
            })

        self.tagging_annos = []
        for tag, rect_list in self.tags.items():
            for rect in rect_list:
                self.tagging_annos.append({
                    'motivation': 'tagging',
                    'body': {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': tag
                    },
                    'target': {
                        'source': 'example.com',
                        'selector': {
                            'conformsTo': 'http://www.w3.org/TR/media-frags/',
                            'type': 'FragmentSelector',
                            'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                                    rect['y'],
                                                                    rect['w'],
                                                                    rect['h'])
                        }
                    }
                })

        self.transcription_annos = []
        for tag, value_list in transcription_data.items():
            for value in value_list:
                self.transcription_annos.append({
                    'motivation': 'describing',
                    'body': [
                        {
                            'type': 'TextualBody',
                            'purpose': 'tagging',
                            'value': tag
                        },
                        {
                            'type': 'TextualBody',
                            'purpose': 'describing',
                            'value': value,
                            'format': 'text/plain'
                        }
                    ],
                    'target': 'example.com'
                })

        self.data = {
            'user_id': [1, 2, 3],
            'info': [
                self.comment_annos,
                self.tagging_annos,
                self.transcription_annos
            ]
        }

    def test_get_comments(self):
        """Test IIIF Annotation comments are returned."""
        task_run_df = pandas.DataFrame(self.data)
        comments = self.iiif_analyst.get_comments(task_run_df)
        expected = [(1, comment) for comment in self.comments]
        assert_equal(comments, expected)

    def test_get_tags(self):
        """Test IIIF Annotation tags are returned."""
        task_run_df = pandas.DataFrame(self.data)
        tags = self.iiif_analyst.get_tags(task_run_df)
        assert_dict_equal(tags, self.tags)

    def test_get_tags_with_body_list(self):
        """Test IIIF Annotation tags are returned when body is a list."""
        self.tagging_annos[0]['body'] = [
            self.tagging_annos[0]['body'],
            {
                'type': 'TextualBody',
                'purpose': 'classifying',
                'value': 'foo'
            }
        ]
        task_run_df = pandas.DataFrame(self.data)
        tags = self.iiif_analyst.get_tags(task_run_df)
        assert_dict_equal(tags, self.tags)

    def test_get_transcriptions_df(self):
        """Test IIIF Annotation transcriptions are returned."""
        task_run_df = pandas.DataFrame(self.data)
        df = self.iiif_analyst.get_transcriptions_df(task_run_df)
        assert_dict_equal(df.to_dict(), self.transcriptions_df.to_dict())

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_analysis_with_no_transcriptions(self, mock_client):
        """Test IIIF analysis with no transcriptions."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'describing',
            'body': [
                {
                    'purpose': 'describing',
                    'value': ''
                },
                {
                    'purpose': 'tagging',
                    'value': 'foo'
                }
            ]
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_fragment_selector_stripped(self, mock_client):
        """Test IIIF fragment selector is stripped if rule applied."""
        n_answers = 3
        source = 'example.com'
        target = {
            'source': source,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh=100,100,100,100'
            }
        }
        rules = dict(remove_fragment_selector=True)
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules=rules,
                                    anno_collection=anno_collection)
        tag = 'foo'
        value = 'bar'
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'describing',
            'body': [
                {
                    'purpose': 'describing',
                    'value': value
                },
                {
                    'purpose': 'tagging',
                    'value': 'foo'
                }
            ]
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
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
                    'value': value,
                    'format': 'text/plain'
                },
                {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                }
            ],
            'target': source
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_comment_annotation_created(self, mock_client):
        """Test IIIF comment annotations are created."""
        n_answers = 1
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target,
                                    anno_collection=anno_collection)
        user = UserFactory()
        value = 'foo'
        TaskRunFactory.create_batch(n_answers, user=user, task=task, info=[
            {
                'motivation': 'commenting',
                'body': {
                    'value': value
                }
            }
        ])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
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
        """Test IIIF transcriptions are normalised according to set rules."""
        n_answers = 1
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        rules = dict(case='title', whitespace='full_stop',
                     trim_punctuation=True)
        task = self.ctx.create_task(n_answers, target, rules=rules,
                                    anno_collection=anno_collection)
        tag = 'foo'
        values = ['HeLLo!', ' hello ', ' hELLO.']
        for value in values:
            TaskRunFactory.create(task=task, info=[
                {
                    'motivation': 'describing',
                    'body': [
                        {
                            'purpose': 'describing',
                            'value': value
                        },
                        {
                            'purpose': 'tagging',
                            'value': tag
                        }
                    ]
                }
            ])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
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
                    'value': 'Hello',
                    'format': 'text/plain'
                },
                {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                }
            ],
            'target': target
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_with_matching_transcriptions(self, mock_client):
        """Test IIIF results with matching transcriptions."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        value = 'foo'
        tag = 'bar'
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'describing',
            'body': [
                {
                    'purpose': 'describing',
                    'value': value
                },
                {
                    'purpose': 'tagging',
                    'value': tag
                }
            ]
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
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
                    'value': value,
                    'format': 'text/plain'
                },
                {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                }
            ],
            'target': target
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_increased_when_not_max(self, mock_client):
        """Test IIIF task redundancy is updated when max not reached."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'describing',
                'body': [
                    {
                        'purpose': 'describing',
                        'value': i
                    },
                    {
                        'purpose': 'tagging',
                        'value': i
                    }
                ]
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers + 1)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_when_max(self, mock_client):
        """Test IIIF task redundancy is not updated when max is reached."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target, max_answers=n_answers)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'describing',
                'body': [
                    {
                        'purpose': 'describing',
                        'value': i
                    },
                    {
                        'purpose': 'tagging',
                        'value': i
                    }
                ]
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_for_tags(self, mock_client):
        """Test IIIF task redundancy is not updated for tags."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'tagging',
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': 'foo'
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{0},{0},{0}'.format(i)
                    }
                }
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_for_comments(self, mock_client):
        """Test IIIF task redundancy is not updated for comments."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'commenting',
                'body': {
                    'type': 'TextualBody',
                    'value': i,
                    'purpose': 'commenting',
                    'format': 'text/plain'
                }
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)

        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_redundancy_not_increased_when_no_values(self, mock_client):
        """Test IIIF task redundancy is not updated when no values."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target,
                                    max_answers=n_answers + 1)
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'describing',
                'body': [
                    {
                        'purpose': 'describing',
                        'value': ''
                    },
                    {
                        'purpose': 'tagging',
                        'value': 'foo'
                    }
                ]
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(updated_task.n_answers, n_answers)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_equal_regions_combined(self, mock_client):
        """Test IIIF equal tag regions are combined."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        rect = dict(x=400, y=200, w=100, h=150)
        tag = 'foo'
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'tagging',
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                            rect['y'],
                                                            rect['w'],
                                                            rect['h'])
                }
            }
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
            'motivation': 'tagging',
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
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                            rect['y'],
                                                            rect['w'],
                                                            rect['h'])
                }
            }
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_equal_regions_combined(self, mock_client):
        """Test IIIF equal tag regions are combined."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        rect = dict(x=400, y=200, w=100, h=150)
        tag = 'foo'
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'tagging',
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                            rect['y'],
                                                            rect['w'],
                                                            rect['h'])
                }
            }
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
            'motivation': 'tagging',
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
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                            rect['y'],
                                                            rect['w'],
                                                            rect['h'])
                }
            }
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_similar_regions_combined(self, mock_client):
        """Test IIIF similar tag regions are combined."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        rect1 = dict(x=90, y=100, w=110, h=90)
        rect2 = dict(x=100, y=110, w=90, h=100)
        rect3 = dict(x=110, y=90, w=100, h=110)
        rects = [rect1, rect2, rect3]
        tag = 'foo'
        for rect in rects:
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'tagging',
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                                rect['y'],
                                                                rect['w'],
                                                                rect['h'])
                    }
                }
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        func = mock_client.create_annotation
        func.assert_called_once_with(anno_collection, {
            'motivation': 'tagging',
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
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh=90,90,120,110'
                }
            }
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_different_regions_combined(self, mock_client):
        """Test IIIF different tag regions are not combined."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection)
        rect1 = dict(x=10, y=10, w=10, h=10)
        rect2 = dict(x=100, y=100, w=100, h=100)
        rect3 = dict(x=200, y=200, w=200, h=200)
        rects = [rect1, rect2, rect3]
        tag = 'foo'
        for rect in rects:
            TaskRunFactory.create(task=task, info=[{
                'motivation': 'tagging',
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                                rect['y'],
                                                                rect['w'],
                                                                rect['h'])
                    }
                }
            }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.iiif_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.call_args_list, [
            call(anno_collection, {
                'motivation': 'tagging',
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
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect1['x'],
                                                                rect1['y'],
                                                                rect1['w'],
                                                                rect1['h'])
                    }
                }
            }),
            call(anno_collection, {
                'motivation': 'tagging',
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
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect2['x'],
                                                                rect2['y'],
                                                                rect2['w'],
                                                                rect2['h'])
                    }
                }
            }),
            call(anno_collection, {
                'motivation': 'tagging',
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
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect3['x'],
                                                                rect3['y'],
                                                                rect3['w'],
                                                                rect3['h'])
                    }
                }
            })
        ])

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_link_added_for_transcription_child_annotations(self, mock_client):
        """Test IIIF linking Annotation created for transcription child."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task_info = dict(parent_annotation_id='anno.example.com/collection/42')
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection,
                                    info=task_info)
        value = 'foo'
        tag = 'bar'
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'describing',
            'body': [
                {
                    'purpose': 'describing',
                    'value': value
                },
                {
                    'purpose': 'tagging',
                    'value': tag
                }
            ]
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_anno_id = 'baz'
        mock_client.create_annotation.return_value = {
            'id': fake_anno_id,
            'type': 'Annotation'
        }
        self.iiif_analyst.analyse(result.id)
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
                        'value': value,
                        'format': 'text/plain'
                    },
                    {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': tag
                    }
                ],
                'target': target
            }),
            call(anno_collection, {
                'motivation': 'linking',
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
                'body': fake_anno_id,
                'target': task_info['parent_annotation_id']
            })
        ])

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_link_added_for_tagging_child_annotations(self, mock_client):
        """Test IIIF linking Annotation created for tagging child."""
        n_answers = 3
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task_info = dict(parent_annotation_id='anno.example.com/collection/42')
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection,
                                    info=task_info)
        tag = 'foo'
        rect = dict(x=400, y=200, w=100, h=150)
        TaskRunFactory.create_batch(n_answers, task=task, info=[{
            'motivation': 'tagging',
            'body': {
                'type': 'TextualBody',
                'purpose': 'tagging',
                'value': tag
            },
            'target': {
                'source': 'example.com',
                'selector': {
                    'conformsTo': 'http://www.w3.org/TR/media-frags/',
                    'type': 'FragmentSelector',
                    'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                            rect['y'],
                                                            rect['w'],
                                                            rect['h'])
                }
            }
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_anno_id = 'baz'
        mock_client.create_annotation.return_value = {
            'id': fake_anno_id,
            'type': 'Annotation'
        }
        self.iiif_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.call_args_list, [
            call(anno_collection, {
                'motivation': 'tagging',
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
                'body': {
                    'type': 'TextualBody',
                    'purpose': 'tagging',
                    'value': tag
                },
                'target': {
                    'source': 'example.com',
                    'selector': {
                        'conformsTo': 'http://www.w3.org/TR/media-frags/',
                        'type': 'FragmentSelector',
                        'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                                rect['y'],
                                                                rect['w'],
                                                                rect['h'])
                    }
                }
            }),
            call(anno_collection, {
                'motivation': 'linking',
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
                'body': fake_anno_id,
                'target': task_info['parent_annotation_id']
            })
        ])

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_link_not_added_for_comment_child_annotations(self, mock_client):
        """Test IIIF linking Annotation not created for comment child."""
        n_answers = 1
        target = 'example.com'
        anno_collection = 'http://eg.com/collection'
        task_info = dict(parent_annotation_id='anno.example.com/collection/42')
        task = self.ctx.create_task(n_answers, target, rules={},
                                    anno_collection=anno_collection,
                                    info=task_info)
        value = 'foo'
        tag = 'bar'
        user = UserFactory()
        TaskRunFactory.create(user=user, task=task, info=[
            {
                'motivation': 'commenting',
                'body': {
                    'value': value
                }
            }
        ])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        fake_anno_id = 'baz'
        mock_client.create_annotation.return_value = {
            'id': fake_anno_id,
            'type': 'Annotation'
        }
        self.iiif_analyst.analyse(result.id)
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
    def test_old_annotations_deleted(self, mock_client):
        """Test IIIF old Annotations deleted."""
        n_answers = 3
        target = 'example.com'
        task = self.ctx.create_task(n_answers, target)
        user = UserFactory()
        TaskRunFactory.create_batch(n_answers, user=user, task=task, info=[
            {
                'motivation': 'commenting',
                'body': {
                    'value': 'foo'
                }
            }
        ])
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
        self.iiif_analyst.analyse(result.id)
        base_url = flask_app.config.get('WEB_ANNOTATION_BASE_URL')
        endpoint = base_url + '/batch/'
        mock_client.delete_batch.assert_called_once_with(fake_annos)
