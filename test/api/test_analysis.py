# -*- coding: utf8 -*-
"""Test analysis API."""

import json
from mock import patch, call
from helper import web
from default import with_context, db, FakeResponse
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository

from pybossa_lc.api import analysis as analysis_api
from pybossa_lc.analysis import z3950, iiif_annotation


class TestAnalysisApi(web.Helper):

    @with_context
    def setUp(self):
        super(TestAnalysisApi, self).setUp()
        self.result_repo = ResultRepository(db)

    @with_context
    @patch('pybossa_lc.api.analysis.Queue.enqueue')
    def test_z930_endpoint(self, mock_enqueue):
        """Test the correct functions are triggered for the Z39.50 endpoint."""
        endpoint = "/libcrowds/analysis/z3950"
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        msg = "The Z39.50 endpoint is listening..."
        assert data['message'] == msg

        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=project.id)[0]
        payload = {
          'event': 'task_completed',
          'project_short_name': project.short_name,
          'project_id': project.id,
          'result_id': result.id,
          'task_id': task.id
        }
        self.app_post_json(endpoint, data=payload)
        payload['all'] = 1
        self.app_post_json(endpoint, data=payload)
        calls = [
          call(z3950.analyse, timeout=600, result_id=result.id),
          call(z3950.analyse, timeout=600, project_id=project.id)
        ]
        mock_enqueue.has_calls(calls)

    @with_context
    @patch('pybossa_lc.api.analysis.Queue.enqueue')
    def test_iiif_endpoint(self, mock_enqueue):
        """Test the correct functions are triggered for the IIIF endpoint."""
        endpoint = "/libcrowds/analysis/iiif-annotation"
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        msg = "The IIIF Annotation endpoint is listening..."
        assert data['message'] == msg

        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=project.id)[0]
        payload = {
          'event': 'task_completed',
          'project_short_name': project.short_name,
          'project_id': project.id,
          'result_id': result.id,
          'task_id': task.id
        }
        self.app_post_json(endpoint, data=payload)
        payload['all'] = 1
        self.app_post_json(endpoint, data=payload)
        calls = [
          call(iiif_annotation.analyse, timeout=600, result_id=result.id),
          call(iiif_annotation.analyse, timeout=600, project_id=project.id)
        ]
        mock_enqueue.has_calls(calls)

    @with_context
    def test_response_message(self):
        """Test the basic response message."""
        res = analysis_api.respond('Hello', foo='bar')
        assert res.mimetype == 'application/json'
        assert res.status_code == 200
        assert json.loads(res.data) == {
            'status': 200,
            'message': 'Hello',
            'foo': 'bar'
        }

    def test_invalid_event_rejected(self):
        """Test that a non-task_completed event is rejected"""
        pass

    def test_non_empty_result_rejected_if_anon(self):
        """Test that a non-empty result is rejected for anon users."""
        pass

    def test_non_empty_result_rejected_if_not_owner(self):
        """Test that a non-empty result is rejected for non-owners."""
        pass

    def test_non_empty_result_analysed_if_owner(self):
        """Test that a non-empty result is analysed for owners."""
        pass

    def test_non_empty_result_analysed_if_admin(self):
        """Test that a non-empty result is analysed for admin."""
        pass
