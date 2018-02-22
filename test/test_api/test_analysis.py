# -*- coding: utf8 -*-
"""Test analysis API."""

import json
from mock import patch
from nose.tools import *
from helper import web
from default import with_context, db
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory
from pybossa.repositories import ResultRepository, UserRepository

from pybossa_lc.api import analysis as analysis_api


class TestAnalysisApi(web.Helper):

    def setUp(self):
        super(TestAnalysisApi, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)

    def create_payload(self, presenter):
        self.register()
        owner = self.user_repo.get(1)
        category = CategoryFactory(info=dict(presenter=presenter))
        project = ProjectFactory(category=category, owner=owner)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project, user=owner)
        result = self.result_repo.get_by(task_id=task.id)
        return {
            'event': 'task_completed',
            'project_short_name': project.short_name,
            'project_id': project.id,
            'result_id': result.id,
            'task_id': task.id
        }

    @with_context
    @patch('pybossa_lc.api.analysis.analyse_single')
    def test_single_z3950_result_analysed(self, mock_analyse_single):
        """Test analysis triggered for a single Z39.50 result."""
        endpoint = "/lc/analysis/"
        presenter = 'z3950'
        payload = self.create_payload(presenter)
        result_id = payload['result_id']
        self.app_post_json(endpoint, data=payload)
        mock_analyse_single.assert_called_once_with(result_id, presenter)

    @with_context
    @patch('pybossa_lc.api.analysis.analyse_single')
    def test_single_iiif_annotation_result_analysed(self, mock_analyse_single):
        """Test analysis triggered for a single IIIF Annotation result."""
        endpoint = "/lc/analysis/"
        presenter = 'iiif-annotation'
        payload = self.create_payload(presenter)
        result_id = payload['result_id']
        self.app_post_json(endpoint, data=payload)
        mock_analyse_single.assert_called_once_with(result_id, presenter)

    @with_context
    def test_results_not_analysed_for_invalid_presenter(self):
        """Test analysis not triggered for an invalid task presenter."""
        endpoint = "/lc/analysis/"
        presenter = 'foo'
        payload = self.create_payload(presenter)
        res = self.app_post_json(endpoint, data=payload)
        data = json.loads(res.data)
        assert_equal(data['code'], 400)

    @with_context
    def test_result_not_analysed_for_invalid_event(self):
        """Test analysis not triggered for a single IIIF Annotation result."""
        endpoint = "/lc/analysis/"
        presenter = 'z3950'
        payload = self.create_payload(presenter)
        payload['event'] = 'foo'
        res = self.app_post_json(endpoint, data=payload)
        data = json.loads(res.data)
        assert_equal(data['code'], 400)

    @with_context
    @patch('pybossa_lc.api.analysis.analyse_all')
    def test_all_results_analysed(self, mock_analyse_all):
        """Test analysis triggered for all results."""
        endpoint = "/lc/analysis/"
        presenter = 'iiif-annotation'
        payload = self.create_payload(presenter)
        payload['all'] = True
        project_id = payload['project_id']
        self.app_post_json(endpoint, data=payload)
        mock_analyse_all.assert_called_once_with(project_id, presenter)

    @with_context
    @patch('pybossa_lc.api.analysis.analyse_empty')
    def test_empty_results_analysed(self, mock_analyse_empty):
        """Test analysis triggered for empty results."""
        endpoint = "/lc/analysis/"
        presenter = 'iiif-annotation'
        payload = self.create_payload(presenter)
        payload['empty'] = True
        project_id = payload['project_id']
        self.app_post_json(endpoint, data=payload)
        mock_analyse_empty.assert_called_once_with(project_id, presenter)

    @with_context
    def test_analysis_get_response(self):
        """Test basic GET response from analysis endpoint."""
        endpoint = "/lc/analysis/"
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_dict_equal(data, {
            'status': 200,
            'message': 'The analysis endpoint is listening...'
        })

    @with_context
    def test_response_message(self):
        """Test the basic response message."""
        msg = 'foo'
        res = analysis_api.respond(msg)
        data = json.loads(res.data)
        assert_equal(res.mimetype, 'application/json')
        assert_equal(res.status_code, 200)
        assert_dict_equal(data, {
            'status': 200,
            'message': msg
        })
