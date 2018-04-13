# -*- coding: utf8 -*-
"""Test annotations API."""

import json
import uuid
from mock import patch
from nose.tools import *
from helper import web
from default import with_context, db, flask_app
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory
from pybossa.repositories import ResultRepository, UserRepository

class TestAnnotationsApi(web.Helper):

    def setUp(self):
        super(TestAnnotationsApi, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)

    def create_annotation(self, tag, value):
        """Create a fake annotation."""
        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        anno_uuid = str(uuid.uuid4())
        _id = '{0}/lc/annotations/wa/{1}'.format(spa_server_name, anno_uuid)
        return {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": _id,
            "type": "Annotation",
            "body": [
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
            "motivation": "describing",
            "target": "http://example.org",
            "created": "2018-04-07T21:38:53Z",
            "generated": "2018-04-07T21:38:53Z"
        }

    @with_context
    def test_valid_annotation_response(self):
        """Test response complies with WA protocol."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)
        anno = self.create_annotation('foo', 'bar')
        result.info = dict(annotations=[anno])
        self.result_repo.update(result)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        endpoint = anno['id'][len(spa_server_name):]
        res = self.app_get_json(endpoint)

        # Check for valid Content-Type
        profile = '"http://www.w3.org/ns/anno.jsonld"'
        content_type = 'application/ld+json; profile={0}'.format(profile)
        assert_equal(res.headers['Content-Type'], content_type)
