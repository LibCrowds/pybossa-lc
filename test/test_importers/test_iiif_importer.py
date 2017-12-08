# -*- coding: utf8 -*-
"""Test IIIF importer."""

import os
import json
from nose.tools import assert_equal
from default import Test, db
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from pybossa.repositories import ResultRepository

from pybossa_lc.importers.iiif import BulkTaskIIIFImporter


class TestIIIFImporter(Test):

    def setUp(self):
        super(TestIIIFImporter, self).setUp()
        self.result_repo = ResultRepository(db)
        manifest_path = os.path.join('test', 'fixtures', 'manifest.json')
        self.manifest = json.load(open(manifest_path))

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
            print task['form']
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
