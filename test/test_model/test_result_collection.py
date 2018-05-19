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
        result_collection = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        user = UserFactory.create()
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        anno = result_collection.add_comment(result, target, value, user)
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

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_tag(self, mock_client):
        """Test that a tagging Annotation is added."""
        iri = 'example.com'
        result_collection = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        anno = result_collection.add_tag(result, target, value)
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

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_tag_with_fragment(self, mock_client):
        """Test that a tagging Annotation is added with a FragmentSelector."""
        iri = 'example.com'
        result_collection = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        rect = dict(x=100, y=100, w=50, h=50)
        anno = result_collection.add_tag(result, target, value, rect)
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

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_add_transcription(self, mock_client):
        """Test that a describing Annotation is added."""
        iri = 'example.com'
        result_collection = ResultCollection(iri)
        target = 'foo'
        value = 'bar'
        tag = 'baz'
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        result = Result(project_id=1, task_run_ids=[])
        rect = dict(x=100, y=100, w=50, h=50)
        anno = result_collection.add_transcription(result, target, value, tag)
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