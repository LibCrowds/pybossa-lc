# -*- coding: utf8 -*-
"""Test result collection model."""

from flask import current_app
from nose.tools import *
from mock import patch
from default import Test, with_context, flask_app
from requests.exceptions import HTTPError
from factories import UserFactory
from pybossa.model.result import Result
from flask import url_for

from pybossa_lc.model.base import Base
from pybossa_lc.model.result_collection import ResultCollection


class TestResultCollection(Test):

    def setUp(self):
        super(TestResultCollection, self).setUp()
        assert_dict_equal.__self__.maxDiff = None

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_comment(self, mock_client):
        """Test that a comment Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        user = UserFactory.create()
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        anno = rc.add_comment(result, target, value, user)
        assert_dict_equal(anno, {
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
        mock_client.create_annotation.assert_called_once_with(iri, anno)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_tag(self, mock_client):
        """Test that a tagging Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        anno = rc.add_tag(result, target, value)
        assert_dict_equal(anno, {
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
        mock_client.create_annotation.assert_called_once_with(iri, anno)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_tag_with_fragment(self, mock_client):
        """Test that a tagging Annotation is added with a FragmentSelector."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        rect = dict(x=100, y=100, w=50, h=50)
        anno = rc.add_tag(result, target, value, rect)
        assert_dict_equal(anno, {
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
        mock_client.create_annotation.assert_called_once_with(iri, anno)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_transcription(self, mock_client):
        """Test that a describing Annotation is added."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        tag = 'baz'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        rect = dict(x=100, y=100, w=50, h=50)
        anno = rc.add_transcription(result, target, value, tag)
        assert_dict_equal(anno, {
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
        mock_client.create_annotation.assert_called_once_with(iri, anno)

    @patch('pybossa_lc.model.base.wa_client')
    def test_error_when_invalid_comment_values(self, mock_client):
        """Test ValueError raised when invalid comment values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        result = Result(project_id=1, task_run_ids=[])
        required = ['target', 'value']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_comment(result, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @patch('pybossa_lc.model.base.wa_client')
    def test_error_when_invalid_tag_values(self, mock_client):
        """Test ValueError raised when invalid tag values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        result = Result(project_id=1, task_run_ids=[])
        required = ['target', 'value']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_tag(result, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @patch('pybossa_lc.model.base.wa_client')
    def test_error_when_invalid_transcription_values(self, mock_client):
        """Test ValueError raised when invalid transcription values."""
        iri = 'example.com'
        rc = ResultCollection(iri)
        result = Result(project_id=1, task_run_ids=[])
        required = ['target', 'value', 'tag']
        invalid = ['', None]
        for key in required:
            for bad_value in invalid:
                values = {k: 'foo' for k in required}
                values[key] = bad_value
                with assert_raises(ValueError) as exc:
                    rc.add_transcription(result, **values)
                err_msg = exc.exception.message
                assert_equal(err_msg, '"{}" is a required value'.format(key))

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
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
