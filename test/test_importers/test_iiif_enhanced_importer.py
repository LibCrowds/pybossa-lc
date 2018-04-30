# -*- coding: utf8 -*-
"""Test IIIF enhanced importer."""

import json
from mock import patch
from nose.tools import *
from default import Test, FakeResponse, with_context, db
from pybossa.importers import BulkImportException
from pybossa.repositories import ResultRepository
from factories import TaskFactory, TaskRunFactory, ProjectFactory

from pybossa_lc.importers.iiif_enhanced import BulkTaskIIIFEnhancedImporter
from ..fixtures.annotation import AnnotationFixtures

@patch('pybossa.importers.iiif.requests')
class TestBulkTaskIIIFEnhancedImport(Test):

    def setUp(self):
        super(TestBulkTaskIIIFEnhancedImport, self).setUp()
        self.result_repo = ResultRepository(db)
        self.manifest_uri = 'http://example.org/iiif/book1/manifest'
        self.canvas_id_base = 'http://example.org/iiif/book1/canvas/p{0}'
        self.img_id_base = 'http://example.org/images/book1-page{0}-img{1}'

    def create_manifest(self, canvases=1, images=1):
        manifest = {
            '@id': self.manifest_uri,
            'sequences': [
                {
                    'canvases': []
                }
            ]
        }
        for i in range(canvases):
            canvas = {
                '@id': self.canvas_id_base.format(i),
                'images': []
            }
            for j in range(images):
                image = {
                    'resource': {
                        'service': {
                            '@id': self.img_id_base.format(i, j)
                        }
                    }
                }
                canvas['images'].append(image)
            manifest['sequences'][0]['canvases'].append(canvas)
        return manifest

    @with_context
    def test_bl_tasks_created_with_bl_link(self, requests):
        """Test that non-BL tasks are created with a non-BL link."""
        manifest = self.create_manifest()
        wrapper = {
            'okay': 1,
            'received': json.dumps(manifest)
        }
        headers = {'Content-Type': 'application/json'}
        valid_manifest = FakeResponse(text=json.dumps(wrapper),
                                      status_code=200, headers=headers,
                                      encoding='utf-8')
        requests.get.return_value = valid_manifest

        importer = BulkTaskIIIFEnhancedImporter(manifest_uri=self.manifest_uri)
        tasks = importer.tasks()
        assert_equal(len(tasks), 1)

        link_query = '?manifest={}#?cv=0'.format(self.manifest_uri)
        link = 'http://universalviewer.io/uv.html' + link_query
        assert_equal(tasks[0]['info']['link'], link)


    @with_context
    def test_non_bl_tasks_created_with_non_bl_link(self, requests):
        """Test that non-BL tasks are created with a non-BL link."""
        manifest = self.create_manifest()
        bl_manifest_id = 'https://api.bl.uk/metadata/iiif/id/manifest.json'
        manifest['@id'] = bl_manifest_id
        wrapper = {
            'okay': 1,
            'received': json.dumps(manifest)
        }
        headers = {'Content-Type': 'application/json'}
        valid_manifest = FakeResponse(text=json.dumps(wrapper),
                                      status_code=200, headers=headers,
                                      encoding='utf-8')
        requests.get.return_value = valid_manifest

        importer = BulkTaskIIIFEnhancedImporter(manifest_uri=bl_manifest_id)
        tasks = importer.tasks()
        assert_equal(len(tasks), 1)

        link = 'http://access.bl.uk/item/viewer/id#?cv=0'
        assert_equal(tasks[0]['info']['link'], link)

    @with_context
    def test_child_tasks_generated(self, requests):
        """Test that child tasks are generated correctly."""
        n_canvases = 3
        n_images = 1
        manifest = self.create_manifest(canvases=n_canvases, images=n_images)
        wrapper = {
            'okay': 1,
            'received': json.dumps(manifest)
        }
        headers = {'Content-Type': 'application/json'}
        valid_manifest = FakeResponse(text=json.dumps(wrapper),
                                      status_code=200, headers=headers,
                                      encoding='utf-8')
        requests.get.return_value = valid_manifest

        # Create a task for each canvas
        anno_fixtures = AnnotationFixtures()
        parent = ProjectFactory()
        tasks = TaskFactory.create_batch(n_canvases, project=parent,
                                         n_answers=1)

        # Create some annotations for each parent task
        expected = []
        for i, task in enumerate(tasks):
            canvas_id = self.canvas_id_base.format(i)
            for j in range(n_images):
                TaskRunFactory.create(task=task)
                img_id = self.img_id_base.format(i, j)

                annotations = [
                    anno_fixtures.create(motivation='tagging',
                                         source=canvas_id),
                    anno_fixtures.create(motivation='describing',
                                         source=canvas_id),
                    anno_fixtures.create(motivation='commenting',
                                         source=canvas_id)
                ]

                result = self.result_repo.get_by(task_id=task.id)
                result.info = dict(annotations=annotations)
                self.result_repo.update(result)

                # Store expected task data to check later
                link_query = '?manifest={}#?cv={}'.format(self.manifest_uri, i)
                link = 'http://universalviewer.io/uv.html' + link_query
                for anno in annotations[:2]:
                    expected.append({
                        'manifest': self.manifest_uri,
                        'target': anno['target'],
                        'link': link,
                        'tileSource': '{}/info.json'.format(img_id),
                        'url': '{}/full/max/0/default.jpg'.format(img_id),
                        'url_m': '{}/full/240,/0/default.jpg'.format(img_id),
                        'url_b': '{}/full/1024,/0/default.jpg'.format(img_id),
                        'parent_annotation_id': anno['id'],
                        'parent_task_id': task.id
                    })

        importer = BulkTaskIIIFEnhancedImporter(manifest_uri=self.manifest_uri,
                                                parent_id=parent.id)
        tasks = importer.tasks()
        task_info = [task['info'] for task in tasks]
        assert_equal(task_info, expected)


    @with_context
    def test_has_child_key_added_to_parent_results(self, requests):
        """Test that the has_children key is added to parent results."""
        manifest = self.create_manifest()
        wrapper = {
            'okay': 1,
            'received': json.dumps(manifest)
        }
        headers = {'Content-Type': 'application/json'}
        valid_manifest = FakeResponse(text=json.dumps(wrapper),
                                      status_code=200, headers=headers,
                                      encoding='utf-8')
        requests.get.return_value = valid_manifest

        # Create a task for each canvas
        n_tasks = 3
        parent = ProjectFactory()
        tasks = TaskFactory.create_batch(n_tasks, project=parent, n_answers=1)
        for task in tasks:
            TaskRunFactory.create(task=task)
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[])
            self.result_repo.update(result)

        importer = BulkTaskIIIFEnhancedImporter(manifest_uri=self.manifest_uri,
                                                parent_id=parent.id)
        tasks = importer.tasks()

        results = self.result_repo.filter_by(project_id=parent.id)
        result_info = [result.info for result in results]
        expected = [{'annotations': [], 'has_children': True}] * n_tasks
        assert_equal(result_info, expected)

    # Add linking to child results during analysis
