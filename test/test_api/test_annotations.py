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

    def check_response(self, res):
        """Check for a valid JSON-LD annotation response."""
        # Check for valid Content-Type header
        profile = '"http://www.w3.org/ns/anno.jsonld"'
        content_type = 'application/ld+json; profile={0}'.format(profile)
        assert_equal(res.headers.get('Content-Type'), content_type)

        # Check for valid Link header
        link = '<http://www.w3.org/ns/ldp#Resource>; rel="type"'
        assert_equal(res.headers.get('Link'), link)

        # Check for ETag header
        assert_not_equal(res.headers.get('ETag'), None)

        # Check for valid Allow header
        assert_equal(res.headers.get('Allow'), 'GET,OPTIONS,HEAD')

        # Check for valid Vary header
        assert_equal(res.headers.get('Vary'), 'Accept')

    @with_context
    def test_single_annotation_returned(self):
        """Test single Annotation returned."""
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

        self.check_response(res)

        assert_equal(json.loads(res.data), anno)

    @with_context
    def test_annotation_collection_returned(self):
        """Test Annotation Collection returned."""
        self.register()
        owner = self.user_repo.get(1)
        volume = dict(id='foo', name='bar', short_name='bar', importer='baz')
        category = CategoryFactory(info=dict(volumes=[volume]))
        project = ProjectFactory(category=category, owner=owner,
                                 info=dict(volume_id=volume['id']))
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)
        annotations = [self.create_annotation('foo', 'bar')] * 101
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        url_base = '/lc/annotations/wa/collection/volume/{}'
        endpoint = url_base.format(volume['id'])
        res = self.app_get_json(endpoint)

        self.check_response(res)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        assert_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}{1}".format(spa_server_name, endpoint),
            "type": "AnnotationCollection",
            "label": "{0} Annotations".format(volume['name']),
            "total": len(annotations),
            "first": "{0}{1}/page1".format(spa_server_name, endpoint),
            "last": "{0}{1}/page2".format(spa_server_name, endpoint)
        })
