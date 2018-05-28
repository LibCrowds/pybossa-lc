# -*- coding: utf8 -*-
"""Test background jobs."""

from mock import patch
from nose.tools import *
from default import Test, with_context, flask_app

from pybossa_lc import jobs


class TestJobs(Test):

    def setUp(self):
        super(TestJobs, self).setUp()

    @with_context
    @patch('pybossa_lc.jobs.enqueue_job')
    @patch('pybossa_lc.jobs.Analyst')
    def test_analyse_single(self, mock_analyst, mock_enqueue):
        """Test analysis of single result queued."""
        result_id = 42
        presenter = 'my-presenter'
        jobs.analyse_single(result_id, presenter)
        job = dict(name=mock_analyst().analyse,
                   args=[],
                   kwargs={'presenter': presenter, 'result_id': result_id,
                           'silent': False},
                   timeout=flask_app.config.get('TIMEOUT'),
                   queue='high')
        mock_enqueue.assert_called_with(job)

    @with_context
    @patch('pybossa_lc.jobs.enqueue_job')
    @patch('pybossa_lc.jobs.Analyst')
    def test_analyse_empty(self, mock_analyst, mock_enqueue):
        """Test analysis of empty results queued."""
        project_id = 42
        presenter = 'my-presenter'
        timeout = 1 * 60 * 60
        jobs.analyse_empty(project_id, presenter)
        job = dict(name=mock_analyst().analyse_empty,
                   args=[],
                   kwargs={'presenter': presenter, 'project_id': project_id},
                   timeout=timeout,
                   queue='high')
        mock_enqueue.assert_called_with(job)

    @with_context
    @patch('pybossa_lc.jobs.enqueue_job')
    @patch('pybossa_lc.jobs.Analyst')
    def test_analyse_all(self, mock_analyst, mock_enqueue):
        """Test analysis of all results queued."""
        project_id = 42
        presenter = 'my-presenter'
        timeout = 1 * 60 * 60
        jobs.analyse_all(project_id, presenter)
        job = dict(name=mock_analyst().analyse_all,
                   args=[],
                   kwargs={'presenter': presenter, 'project_id': project_id},
                   timeout=timeout,
                   queue='high')
        mock_enqueue.assert_called_with(job)
