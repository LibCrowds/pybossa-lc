# -*- coding: utf8 -*-
"""Test result collection model."""

import itertools
from nose.tools import *
from mock import patch
from default import Test, with_context, flask_app
from requests.exceptions import HTTPError
from factories import UserFactory, TaskFactory
from pybossa.model.result import Result
from flask import url_for, current_app

from pybossa_lc.model.base import Base
from pybossa_lc.model.result_collection import ResultCollection


@patch('pybossa_lc.model.base.wa_client')
class TestResultCollection(Test):

    def setUp(self):
        super(TestResultCollection, self).setUp()
        assert_dict_equal.__self__.maxDiff = None

    @with_context
    def test_add_comment(self, mock_client):
        """Test that a comment Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        user = UserFactory.create()
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        fake_anno = dict(foo='bar')
        mock_client.create_annotation.return_value = fake_anno
        anno = rc.add_comment(result, task, target, value, user)
        assert_equal(anno, fake_anno)
        mock_client.create_annotation.assert_called_once_with(iri, {
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
    def test_add_tag(self, mock_client):
        """Test that a tagging Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        fake_anno = dict(foo='bar')
        mock_client.create_annotation.return_value = fake_anno
        anno = rc.add_tag(result, task, target, value)
        assert_equal(anno, fake_anno)
        mock_client.create_annotation.assert_called_once_with(iri, {
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
                'value': value
            },
            'target': target
        })

    @with_context
    def test_add_tag_with_fragment(self, mock_client):
        """Test that a tagging Annotation is added with a FragmentSelector."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        rect = dict(x=100, y=100, w=50, h=50)
        fake_anno = dict(foo='bar')
        mock_client.create_annotation.return_value = fake_anno
        anno = rc.add_tag(result, task, target, value, rect)
        assert_equal(anno, fake_anno)
        mock_client.create_annotation.assert_called_once_with(iri, {
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
                'value': value
            },
            'target': {
                'source': target,
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
    def test_add_transcription(self, mock_client):
        """Test that a describing Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        tag = 'baz'
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        fake_anno = dict(foo='bar')
        mock_client.create_annotation.return_value = fake_anno
        anno = rc.add_transcription(result, task, target, value, tag)
        assert_equal(anno, fake_anno)
        mock_client.create_annotation.assert_called_once_with(iri, {
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
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": value,
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": tag
                }
            ],
            'target': target
        })

    @with_context
    def test_error_when_invalid_comment_values(self, mock_client):
        """Test ValueError raised when invalid comment values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        required = ['target', 'value']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_comment(result, task, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @with_context
    def test_error_when_invalid_tag_values(self, mock_client):
        """Test ValueError raised when invalid tag values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        required = ['target', 'value']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_tag(result, task, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @with_context
    def test_error_when_invalid_transcription_values(self, mock_client):
        """Test ValueError raised when invalid transcription values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        required = ['target', 'value', 'tag']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_transcription(result, task, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @with_context
    def test_annotations_searched_by_result(self, mock_client):
        """Test Annotations are searched for by result."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        result = Result(project_id=1, task_run_ids=[])
        rc.get_by_result(result)
        contains = {
            'generator': [
                {
                    'id': url_for('api.api_result', oid=result.id),
                    'type': 'Software'
                }
            ]
        }
        mock_client.search_annotations.assert_called_once_with(iri, contains)

    @with_context
    def test_batch_delete_annotations(self, mock_client):
        """Test Annotations are deleted."""
        rc = ResultCollection(None)
        annos = [
            {
                'id': 'foo',
                'type': 'Annotation'
            },
            {
                'id': 'bar',
                'type': 'Annotation'
            }
        ]
        rc.delete_batch(annos)
        mock_client.delete_batch.assert_called_once_with(annos)

    @with_context
    def test_transcription_values_validated(self, mock_client):
        """Test validation for required transcription values."""
        rc = ResultCollection(None)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        # Check it doesn't raise exception for valid values
        rc.add_transcription(result, task, 'example.com', u'\xa3', 42)
        # Then check empty string and None for each required value
        for comb in itertools.combinations(['foo', 'bar', '', None], 3):
            assert_raises(ValueError, rc.add_transcription, result, task,
                          comb[0], comb[1], comb[2])

    @with_context
    def test_tagging_values_validated(self, mock_client):
        """Test validation for required tagging values."""
        rc = ResultCollection(None)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        # Check it doesn't raise exception for valid values
        rc.add_tag(result, task, 'example.com', u'\xa3')
        # Then check empty string and None for each required value
        for comb in itertools.combinations(['foo', '', None], 2):
            assert_raises(ValueError, rc.add_tag, result, task, comb[0],
                          comb[1])

    @with_context
    def test_comment_values_validated(self, mock_client):
        """Test validation for required comment values."""
        rc = ResultCollection(None)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        # Check it doesn't raise exception for valid values
        rc.add_comment(result, task, 'example.com', u'\xa3')
        # Then check empty string and None for each required value
        for comb in itertools.combinations(['foo', '', None], 2):
            assert_raises(ValueError, rc.add_comment, result, task, comb[0],
                          comb[1])

    @with_context
    def test_get_annotation_base(self, mock_client):
        """Test get Annotation base."""
        rc = ResultCollection(None)
        task = TaskFactory()
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        motivation = 'foo'
        base = rc._get_annotation_base(result, task, motivation)
        assert_equal(base, {
            'type': 'Annotation',
            'motivation': motivation,
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
            ]
        })

    @with_context
    def test_get_annotation_base_with_manifest(self, mock_client):
        """Test get Annotation base with a manifest."""
        rc = ResultCollection(None)
        manifest = 'example.com'
        task = TaskFactory(info=dict(manifest=manifest))
        result = Result(project_id=1, task_id=task.id, task_run_ids=[])
        motivation = 'foo'
        base = rc._get_annotation_base(result, task, motivation)
        assert_equal(base, {
            'type': 'Annotation',
            'motivation': motivation,
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
            'partOf': manifest
        })
