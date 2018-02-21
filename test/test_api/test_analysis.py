# -*- coding: utf8 -*-
"""Test analysis API."""

import json
from mock import patch, call
from helper import web
from default import with_context, db
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository, UserRepository

from pybossa_lc.api import analysis as analysis_api
from pybossa_lc.analysis import z3950, iiif_annotation


class TestAnalysisApi(web.Helper):

    def setUp(self):
        super(TestAnalysisApi, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)

    @with_context
    @patch('pybossa_lc.api.analysis.enqueue_job')
    def test_z3950_single_result_analysed(self, mock_enqueue):
        """Test analysis triggered for a single Z39.50 result."""
        endpoint = "/lc/analysis/z3950"
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
        job = dict(name=z3950.analyse,
                   args=[],
                   kwargs={'result_id': result.id},
                   timeout=self.flask_app.config.get('TIMEOUT'),
                   queue='high')
        mock_enqueue.assert_called_once_with(job)

    @with_context
    @patch('pybossa_lc.api.analysis.enqueue_job')
    def test_z3950_all_results_analysed(self, mock_enqueue):
        """Test analysis triggered for all Z39.50 results."""
        endpoint = "/lc/analysis/z3950"
        self.register()
        owner = self.user_repo.get(1)
        project = ProjectFactory.create(owner=owner)
        payload = {
            'event': 'task_completed',
            'project_short_name': project.short_name,
            'project_id': project.id,
            'all': 1
        }
        self.app_post_json(endpoint, data=payload)
        job = dict(name=z3950.analyse_all,
                   args=[],
                   kwargs={'project_id': project.id},
                   timeout=self.flask_app.config.get('TIMEOUT'),
                   queue='high')
        mock_enqueue.assert_called_once_with(job)

    @with_context
    @patch('pybossa_lc.api.analysis.enqueue_job')
    def test_iiif_annotation_single_result_analysed(self, mock_enqueue):
        """Test analysis triggered for a single IIIF Annotation result."""
        endpoint = "/lc/analysis/iiif-annotation"
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
        job = dict(name=iiif_annotation.analyse,
                   args=[],
                   kwargs={'result_id': result.id},
                   timeout=self.flask_app.config.get('TIMEOUT'),
                   queue='high')
        mock_enqueue.assert_called_once_with(job)

    @with_context
    @patch('pybossa_lc.api.analysis.enqueue_job')
    def test_iiif_annotation_all_results_analysed(self, mock_enqueue):
        """Test analysis triggered for all IIIF Annotation results."""
        endpoint = "/lc/analysis/iiif-annotation"
        self.register()
        owner = self.user_repo.get(1)
        project = ProjectFactory.create(owner=owner)
        payload = {
            'event': 'task_completed',
            'project_short_name': project.short_name,
            'project_id': project.id,
            'all': 1
        }
        self.app_post_json(endpoint, data=payload)
        job = dict(name=iiif_annotation.analyse_all,
                   args=[],
                   kwargs={'project_id': project.id},
                   timeout=self.flask_app.config.get('TIMEOUT'),
                   queue='high')
        mock_enqueue.assert_called_once_with(job)

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
