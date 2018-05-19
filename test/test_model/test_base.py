# -*- coding: utf8 -*-
"""Test base model."""

from nose.tools import *
from mock import patch
from default import Test, with_context, flask_app
from requests.exceptions import HTTPError
from factories import UserFactory
from flask import url_for
from pybossa.model.result import Result

from pybossa_lc.model.base import Base


class TestBaseModel(Test):

    @patch('pybossa_lc.model.base.wa_client')
    def test_iri_checked_on_init(self, mock_client):
        """Test IRI checked on initialisation."""
        iri = 'example.com'
        Base(iri)
        mock_client.get_collection.assert_called_once_with(iri)

    @patch('pybossa_lc.model.base.wa_client')
    def test_create_annotation(self, mock_client):
        """Test Annotation creted."""
        iri = 'example.com'
        anno = {
            'foo': 'bar'
        }
        base = Base(iri)
        base._create_annotation(anno)
        mock_client.create_annotation.assert_called_once_with(iri, anno)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_get_creator(self, mock_client):
        """Test that the correct Annotation creator is returned."""
        base = Base(None)
        user = UserFactory.create()
        creator = base._get_creator(user)
        assert_dict_equal(creator, {
            'id': url_for('api.api_user', oid=user.id, _external=True),
            'type': 'Person',
            'name': user.fullname,
            'nickname': user.name
        })

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_get_generator(self, mock_client):
        """Test that the correct Annotation generator is returned."""
        base = Base(None)
        result = Result(project_id=1, task_run_ids=[])
        generator = base._get_generator(result)
        assert_equal(generator, [
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
        ])
