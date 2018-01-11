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
        importer = BulkTaskIIIFImporter(None, None, None)
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
        importer = BulkTaskIIIFImporter(manifest_uri, None, project.id)
        importer._generate_tasks()
        mock_enhance.assert_called_with(task_data, project.id)

    def test_task_count(self):
        """Test that tasks are counted correctly."""
        n_tasks = 42
        importer = BulkTaskIIIFImporter(None, None, None)
        mock_generate = MagicMock()
        mock_generate.return_value = [{}] * n_tasks
        importer._generate_tasks = mock_generate
        count = importer.count_tasks()
        assert count == n_tasks

    def test_get_default_share_url(self):
        """Test get default share URL."""
        _id = '123'
        manifest_uri = 'http://example.com/iiif/{}/manifest.json'.format(_id)
        importer = BulkTaskIIIFImporter(manifest_uri, None, None)
        canvas_index = 10
        share_url = importer._get_share_url(manifest_uri, canvas_index)
        base = 'http://universalviewer.io/uv.html'
        expected_url = '{0}?manifest={1}#?cv={2}'.format(base, manifest_uri,
                                                         canvas_index)
        assert share_url == expected_url

    def test_get_bl_share_url(self):
        """Test get BL share URL."""
        _id = 'ark:/81055/vdc_100022589138.0x000002'
        base = 'http://api.bl.uk/metadata/iiif'
        manifest_uri = '{}/{}/manifest.json'.format(base, _id)
        importer = BulkTaskIIIFImporter(manifest_uri, None, None)
        canvas_index = 10
        share_url = importer._get_share_url(manifest_uri, canvas_index)
        expected_base = 'http://access.bl.uk/item/viewer/'
        expected_url = '{0}{1}#?cv={2}'.format(expected_base, _id,
                                               canvas_index)
        assert share_url == expected_url

    @with_context
    def test_get_select_task_data_from_manifest(self):
        """Test that select task data is generated from a manifest."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        user = UserFactory.create(info=dict(templates=[tmpl]))
        self.user_repo.update(user)
        manifest_uri = self.manifest['@id']

        importer = BulkTaskIIIFImporter(manifest_uri, tmpl['id'], None)
        task_data = importer._get_task_data(self.manifest)
        canvases = self.manifest['sequences'][0]['canvases']
        assert len(task_data) == len(canvases)
        for idx, task in enumerate(task_data):
            img = canvases[idx]['images'][0]['resource']['service']['@id']
            assert_dict_equal(task, {
                'info': self.manifest['@id'],
                'target': canvases[idx]['@id'],
                'guidance': tmpl['task']['guidance'],
                'shareUrl': importer._get_share_url(manifest_uri, idx),
                'tileSource': '{}/info.json'.format(img),
                'tag': tmpl['task']['tag'],
                'mode': tmpl['task']['mode'],
                'objective': tmpl['task']['objective'],
                'thumbnailUrl': '{}/full/256,/0/default.jpg'.format(img)
            })

    @with_context
    def test_get_transcribe_task_data_from_manifest(self):
        """Test that transcribe task data is generated from a manifest."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        transcribe_task = tmpl_fixtures.iiif_transcribe_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=transcribe_task)
        user = UserFactory.create(info=dict(templates=[tmpl]))
        self.user_repo.update(user)
        manifest_uri = self.manifest['@id']

        importer = BulkTaskIIIFImporter(manifest_uri, tmpl['id'], None)
        task_data = importer._get_task_data(self.manifest)
        canvases = self.manifest['sequences'][0]['canvases']
        assert len(task_data) == len(canvases)
        for idx, task in enumerate(task_data):
            img = canvases[idx]['images'][0]['resource']['service']['@id']
            assert_dict_equal(task, {
                'info': self.manifest['@id'],
                'target': canvases[idx]['@id'],
                'guidance': tmpl['task']['guidance'],
                'shareUrl': importer._get_share_url(manifest_uri, idx),
                'tileSource': '{}/info.json'.format(img),
                'tag': tmpl['task']['tag'],
                'mode': tmpl['task']['mode'],
                'objective': tmpl['task']['objective'],
                'thumbnailUrl': '{}/full/256,/0/default.jpg'.format(img),
                'form': {
                    'model': {
                        'title': ''
                    },
                    'schema': {
                        'fields': tmpl['task']['fields_schema']
                    }
                }
            })

    @with_context
    def test_enhance_task_data_from_tagging_parent(self):
        """Test that a transcription task is created for each parent result."""
        annotations = []
        n_annos = 3
        target = 'http://example.org/iiif/book1/canvas/p1'
        for i in range(n_annos):
            anno = copy.deepcopy(self.select_annotation)
            selection = '?xywh={0},{0},{0},{0}'.format(i)
            anno['target']['source'] = target
            anno['target']['selector']['value'] = selection
            annotations.append(anno)

        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=project.id)[0]
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)
        task_data = [
            {
                'target': target,
                'mode': 'transcribe'
            }
        ]
        importer = BulkTaskIIIFImporter(None, None, None)
        task_data = importer._enhance_task_data(task_data, project.id)
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
            assert data['parent_task_id'] == task.id

    @with_context
    @raises(ValueError)
    def test_enhance_task_data_throws_error_with_unhandled_motivation(self):
        """Test that an unhandled motivvation throws an error."""
        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=project.id)[0]
        result.info = dict(annotations=[self.transcribe_annotation])
        self.result_repo.update(result)
        task_data = [
            {
                'target': 'some_target',
                'mode': 'select'
            }
        ]
        importer = BulkTaskIIIFImporter(None, None, None)
        importer._enhance_task_data(task_data, project.id)

    @with_context
    @raises(ValueError)
    def test_enhance_task_data_throws_error_with_empty_result(self):
        """Test that an empty result throws an error."""
        project = ProjectFactory.create()
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        task_data = []
        importer = BulkTaskIIIFImporter(None, None, None)
        importer._enhance_task_data(task_data, project.id)
