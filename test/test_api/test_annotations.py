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
        assert_dict_equal.__self__.maxDiff = None

    def create_annotation(self, motivation='describing'):
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
                    "value": "foo",
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": "bar"
                }
            ],
            "motivation": motivation,
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

        anno = self.create_annotation()
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
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        per_page = flask_app.config.get('ANNOTATIONS_PER_PAGE')
        annotations = []
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        query_str = 'foo=bar'
        endpoint = '/lc/annotations/wa/collection/{}'.format(category.id)
        res = self.app_get_json(endpoint + '?' + query_str)

        self.check_response(res)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        id_uri = spa_server_name + endpoint

        assert_dict_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}?{1}".format(id_uri, query_str),
            "type": "AnnotationCollection",
            "label": u"{0} Annotations".format(category.name),
            "total": len(annotations)
        })

    @with_context
    def test_annotation_collection_returned_with_first(self):
        """Test first URI in Annotation Collection if more than zero pages."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        annotations = [self.create_annotation()]
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        query_str = 'foo=bar'
        endpoint = '/lc/annotations/wa/collection/{}'.format(category.id)
        res = self.app_get_json(endpoint + '?' + query_str)

        self.check_response(res)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        id_uri = spa_server_name + endpoint

        assert_dict_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}?{1}".format(id_uri, query_str),
            "type": "AnnotationCollection",
            "label": u"{0} Annotations".format(category.name),
            "total": len(annotations),
            "first": "{0}/1?{1}".format(id_uri, query_str)
        })


    @with_context
    def test_annotation_collection_returned_with_last(self):
        """Test last URI in Annotation Collection if more than one page."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        per_page = flask_app.config.get('ANNOTATIONS_PER_PAGE')
        annotations = [self.create_annotation()] * (per_page + 1)
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        query_str = 'foo=bar'
        endpoint = '/lc/annotations/wa/collection/{}'.format(category.id)
        res = self.app_get_json(endpoint + '?' + query_str)

        self.check_response(res)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        id_uri = spa_server_name + endpoint

        assert_dict_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}?{1}".format(id_uri, query_str),
            "type": "AnnotationCollection",
            "label": u"{0} Annotations".format(category.name),
            "total": len(annotations),
            "first": "{0}/1?{1}".format(id_uri, query_str),
            "last": "{0}/2?{1}".format(id_uri, query_str)
        })

    @with_context
    def test_annotation_page_returned(self):
        """Test Annotation Page returned."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        per_page = flask_app.config.get('ANNOTATIONS_PER_PAGE')
        annotations = [self.create_annotation()] * (per_page + 1)
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        page = 1
        query_str = 'foo=bar'
        url_base = '/lc/annotations/wa/collection/{0}'.format(category.id)
        endpoint = '{0}/{1}'.format(url_base, page)
        res = self.app_get_json(endpoint + '?' + query_str)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        coll_id_uri = spa_server_name + url_base

        assert_dict_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}/{1}?{2}".format(coll_id_uri, page, query_str),
            "type": "AnnotationPage",
            "partOf": {
                "id": "{0}?{1}".format(coll_id_uri, query_str),
                "label": u"{0} Annotations".format(category.name),
                "total": len(annotations)
            },
            "next": "{0}/{1}?{2}".format(coll_id_uri, page + 1, query_str),
            "startIndex": 0,
            "items": annotations[:per_page * page]
        })

    @with_context
    def test_404_if_annotation_page_empty(self):
        """Test 404 returned if Annotation Page is empty."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        per_page = flask_app.config.get('ANNOTATIONS_PER_PAGE')
        annotations = [self.create_annotation()] * per_page
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        page = len(annotations) + 1
        url_base = '/lc/annotations/wa/collection/{0}'.format(category.id)
        endpoint = '{0}/{1}'.format(url_base, page)
        res = self.app_get_json(endpoint)

        assert_equal(res.status_code, 404)

    @with_context
    def test_annotation_page_returned_with_iris_only(self):
        """Test Annotation Page returned with IRIs only."""
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory()
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)

        per_page = flask_app.config.get('ANNOTATIONS_PER_PAGE')
        annotations = [self.create_annotation()] * (per_page + 1)
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        page = 1
        query_str = 'iris=1'
        url_base = '/lc/annotations/wa/collection/{0}'.format(category.id)
        endpoint = '{0}/{1}'.format(url_base, page)
        res = self.app_get_json(endpoint + '?' + query_str)

        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        coll_id_uri = spa_server_name + url_base

        assert_dict_equal(json.loads(res.data), {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "{0}/{1}?{2}".format(coll_id_uri, page, query_str),
            "type": "AnnotationPage",
            "partOf": {
                "id": "{0}?{1}".format(coll_id_uri, query_str),
                "label": u"{0} Annotations".format(category.name),
                "total": len(annotations)
            },
            "next": "{0}/{1}?{2}".format(coll_id_uri, page + 1, query_str),
            "startIndex": 0,
            "items": [anno['id'] for anno in annotations[:per_page * page]]
        })
