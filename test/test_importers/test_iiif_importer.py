# -*- coding: utf8 -*-
"""Test IIIF importer."""

import os
import json
import copy
from mock import MagicMock, patch
from nose.tools import assert_equal
from default import Test, db, with_context
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository

from pybossa_lc.importers.iiif import BulkTaskIIIFImporter


class TestIIIFImporter(Test):

    def setUp(self):
        super(TestIIIFImporter, self).setUp()
        self.result_repo = ResultRepository(db)
        manifest_path = os.path.join('test', 'fixtures', 'manifest.json')
        select_anno_path = os.path.join('test', 'fixtures',
                                        'select_annotation.json')
        self.manifest = json.load(open(manifest_path))
        self.select_annotation = json.load(open(select_anno_path))

    def test_get_default_share_url(self):
        """Test get default share URL."""
        _id = '123'
        manifest_url = 'http://example.com/iiif/{}/manifest.json'.format(_id)
        importer = BulkTaskIIIFImporter(manifest_url, None)
        canvas_index = 10
        share_url = importer._get_share_url(manifest_url, canvas_index)
        base = 'http://universalviewer.io/uv.html'
        expected_url = '{0}?manifest={1}#?cv={2}'.format(base, manifest_url,
                                                         canvas_index)
        assert share_url == expected_url

    def test_get_bl_share_url(self):
        """Test get BL share URL."""
        _id = 'ark:/81055/vdc_100022589138.0x000002'
        base = 'http://api.bl.uk/metadata/iiif'
        manifest_url = '{}/{}/manifest.json'.format(base, _id)
        importer = BulkTaskIIIFImporter(manifest_url, None)
        canvas_index = 10
        share_url = importer._get_share_url(manifest_url, canvas_index)
        expected_base = 'http://access.bl.uk/item/viewer/'
        expected_url = '{0}{1}#?cv={2}'.format(expected_base, _id,
                                               canvas_index)
        assert share_url == expected_url

    def test_get_select_task_data_from_manifest(self):
        """Test that select task data is generated from a manifest."""
        manifest_uri = self.manifest['@id']
        template = {
            'mode': 'select',
            'tag': 'title',
            'objective': 'Mark the titles',
            'guidance': 'Mark all of the titles',
            'fields': []
        }
        importer = BulkTaskIIIFImporter(manifest_uri, template)
        task_data = importer._get_task_data_from_manifest(self.manifest)
        canvases = self.manifest['sequences'][0]['canvases']
        assert len(task_data) == len(canvases)
        for idx, task in enumerate(task_data):
            img = canvases[idx]['images'][0]['resource']['service']['@id']
            assert_equal(task, {
                'info': self.manifest['@id'],
                'target': canvases[idx]['@id'],
                'guidance': template['guidance'],
                'shareUrl': importer._get_share_url(manifest_uri, idx),
                'tileSource': '{}/info.json'.format(img),
                'tag': template['tag'],
                'mode': template['mode'],
                'objective': template['objective'],
                'thumbnailUrl': '{}/full/256,/0/default.jpg'.format(img)
            })

    def test_get_transcribe_task_data_from_manifest(self):
        """Test that transcribe task data is generated from a manifest."""
        manifest_uri = self.manifest['@id']
        template = {
            'mode': 'transcribe',
            'tag': 'date',
            'objective': 'Transcribe the date',
            'guidance': 'Transcribe the data as shown',
            'fields': [
                {
                    'model': 'date',
                    'type': 'input',
                    'inputType': 'date',
                    'label': 'Date'
                }
            ]
        }
        importer = BulkTaskIIIFImporter(manifest_uri, template)
        task_data = importer._get_task_data_from_manifest(self.manifest)
        canvases = self.manifest['sequences'][0]['canvases']
        assert len(task_data) == len(canvases)
        for idx, task in enumerate(task_data):
            img = canvases[idx]['images'][0]['resource']['service']['@id']
            assert_equal(task, {
                'info': self.manifest['@id'],
                'target': canvases[idx]['@id'],
                'guidance': template['guidance'],
                'shareUrl': importer._get_share_url(manifest_uri, idx),
                'tileSource': '{}/info.json'.format(img),
                'tag': template['tag'],
                'mode': template['mode'],
                'objective': template['objective'],
                'thumbnailUrl': '{}/full/256,/0/default.jpg'.format(img),
                'form': {
                    'model': {
                      'date': ''
                    },
                    'schema': {
                        'fields': template['fields']
                    }
                }
            })

    @with_context
    def test_enhance_task_data_from_tagging_parent(self):
        """Test that a transcription task is created for each parent result."""
        annotations = []
        n_annos = 3
        parent_task_id = 42
        target = 'http://example.org/iiif/book1/canvas/p1'
        for i in range(n_annos):
            anno = copy.deepcopy(self.select_annotation)
            selection = '?xywh={0},{0},{0},{0}'.format(i)
            anno['target']['source'] = target
            anno['target']['selector']['value'] = selection
            annotations.append(anno)
        results = [
            {
                'task_id': parent_task_id,
                'info': {
                    'annotations': annotations
                }
            }
        ]
        task_data = [
            {
                'target': target,
                'mode': 'transcribe'
            }
        ]

        importer = BulkTaskIIIFImporter(self.manifest['@id'], {})
        task_data = importer._enhance_task_data_from_parent(task_data, results)
        assert len(task_data) == len(annotations)
        for i in range(n_annos):
            data = task_data[i]
            assert data['highlights'] == [
                {
                    'x': float(i),
                    'y': float(i),
                    'width': float(i),
                    'height': float(i)
                }
            ]
            assert data['bounds'] == {
                'x': float(i) + -200,
                'y': float(i) + 0,
                'width': float(i) + 400,
                'height': float(i) + 0
            }
            assert data['parent_task_id'] == parent_task_id

    def test_task_generation_triggered(self):
        """Test that task generation is triggered."""
        importer = BulkTaskIIIFImporter(self.manifest['@id'], {})
        mock_generate = MagicMock()
        importer._generate_tasks = mock_generate
        importer.tasks()
        assert mock_generate.called

    def test_task_count(self):
        """Test that tasks are counted correctly."""
        n_tasks = 42
        importer = BulkTaskIIIFImporter(self.manifest['@id'], {})
        mock_generate = MagicMock()
        mock_generate.return_value = [{}] * n_tasks
        importer._generate_tasks = mock_generate
        count = importer.count_tasks()
        assert count == n_tasks
