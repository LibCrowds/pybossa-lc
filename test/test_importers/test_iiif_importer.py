# -*- coding: utf8 -*-
"""Test IIIF importer."""

import os
import json
import copy
from mock import MagicMock, patch
from nose.tools import *
from default import Test, db, with_context, FakeResponse
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory, UserFactory
from pybossa.repositories import ResultRepository, UserRepository
from pybossa.core import project_repo

from pybossa_lc.importers.iiif import BulkTaskIIIFImporter
from ..fixtures import TemplateFixtures


class TestIIIFImporter(Test):

    def setUp(self):
        super(TestIIIFImporter, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)
        manifest_path = os.path.join('test', 'fixtures', 'manifest.json')
        select_anno_path = os.path.join('test', 'fixtures',
                                        'select_annotation.json')
        transcribe_anno_path = os.path.join('test', 'fixtures',
                                            'transcribe_annotation.json')
        self.manifest = json.load(open(manifest_path))
        self.select_annotation = json.load(open(select_anno_path))
        self.transcribe_annotation = json.load(open(transcribe_anno_path))

    def test_task_generation_triggered(self):
        """Test that task generation is triggered."""
        importer = BulkTaskIIIFImporter(None, None)
        mock_generate = MagicMock()
        importer._generate_tasks = mock_generate
        importer.tasks()
        assert mock_generate.called

    @with_context
    @patch('pybossa_lc.importers.iiif.requests.get')
    @patch('pybossa_lc.importers.iiif.BulkTaskIIIFImporter._get_task_data')
    @patch('pybossa_lc.importers.iiif.BulkTaskIIIFImporter._enhance_task_data')
    def test_task_generation_with_parent(self, mock_enhance, mock_get_data,
                                         mock_get):
        """Test task generation with a parent."""
        mock_get.return_value = MagicMock()
        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        task_data = [
            {
                'target': 'some_target',
                'mode': 'transcribe'
            }
        ]
        manifest_uri = 'http://example.com/iiif/123/manifest.json'
        mock_get_data.return_value = task_data
        importer = BulkTaskIIIFImporter(manifest_uri, project.id)
        importer._generate_tasks()
        mock_enhance.assert_called_with(task_data, project.id)

    def test_task_count(self):
        """Test that tasks are counted correctly."""
        n_tasks = 42
        importer = BulkTaskIIIFImporter(None, None)
        mock_generate = MagicMock()
        mock_generate.return_value = [{}] * n_tasks
        importer._generate_tasks = mock_generate
        count = importer.count_tasks()
        assert count == n_tasks

    def test_get_default_link(self):
        """Test get default share link."""
        _id = '123'
        manifest_uri = 'http://example.com/iiif/{}/manifest.json'.format(_id)
        importer = BulkTaskIIIFImporter(manifest_uri, None)
        canvas_index = 10
        link = importer._get_link(manifest_uri, canvas_index)
        base = 'http://universalviewer.io/uv.html'
        expected_url = '{0}?manifest={1}#?cv={2}'.format(base, manifest_uri,
                                                         canvas_index)
        assert link == expected_url

    @with_context
    def test_get_task_data_from_manifest(self):
        """Test that task data is generated from a manifest."""
        manifest_uri = self.manifest['@id']
        importer = BulkTaskIIIFImporter(manifest_uri, None)
        task_data = importer._get_task_data(self.manifest)
        canvases = self.manifest['sequences'][0]['canvases']
        assert len(task_data) == len(canvases)
        for idx, task in enumerate(task_data):
            img = canvases[idx]['images'][0]['resource']['service']['@id']
            assert_dict_equal(task, {
                'manifest': manifest_uri,
                'target': canvases[idx]['@id'],
                'link': importer._get_link(manifest_uri, idx),
                'tileSource': '{}/info.json'.format(img),
                'url': '{}/full/max/0/default.jpg'.format(img),
                'url_m': '{}/full/240,/0/default.jpg'.format(img),
                'url_b': '{}/full/1024,/0/default.jpg'.format(img)
            })
