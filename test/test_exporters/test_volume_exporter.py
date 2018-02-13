# -*- coding: utf8 -*-
"""Test volume exporter."""

import uuid
import itertools
from nose.tools import *
from default import Test, db, with_context
from factories import CategoryFactory, ProjectFactory, TaskFactory
from factories import TaskRunFactory, UserFactory
from pybossa.repositories import ResultRepository, ProjectRepository

from ..fixtures import TemplateFixtures, AnnotationFixtures
from pybossa_lc.exporters import VolumeExporter

class TestVolumeExporter(Test):

    def setUp(self):
        super(TestVolumeExporter, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)
        self.volume_exporter = VolumeExporter()
        self.category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(self.category)
        self.anno_fixtures = AnnotationFixtures()
        task_tmpl = tmpl_fixtures.iiif_transcribe_tmpl
        self.tmpl = tmpl_fixtures.create_template(task_tmpl=task_tmpl)
        self.volumes = [
            {
                'id': str(uuid.uuid4()),
                'name': 'A Volume',
                'short_name': 'a_volume',
                'source': 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
            }
        ]

    @with_context
    def test_get_json_data_with_one_project(self):
        """Test JSON data with one project and one type of transcription."""
        self.category.info = {
            'volumes': self.volumes
        }
        self.project_repo.update_category(self.category)
        volume_id = self.volumes[0]['id']
        tmpl_id = self.tmpl['id']
        UserFactory.create(info=dict(templates=[self.tmpl]))
        project_info = dict(volume_id=volume_id, template_id=tmpl_id)
        project = ProjectFactory.create(category=self.category,
                                        info=project_info)
        tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

        expected_data = []
        for i, task in enumerate(tasks):
            TaskRunFactory.create(task=task, project=project)
            (annotation, tag, value,
             source) = self.anno_fixtures.create_describing_anno(i)
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[annotation])
            self.result_repo.update(result)
            expected_data.append(annotation)

        data = self.volume_exporter._get_data('describing', volume_id)
        assert_equal(data, expected_data)

    @with_context
    def test_get_json_data_with_multiple_annotations(self):
        """Test get JSON data with multiple annotations."""
        self.category.info = {
            'volumes': self.volumes
        }
        self.project_repo.update_category(self.category)
        volume_id = self.volumes[0]['id']
        tmpl_id = self.tmpl['id']
        UserFactory.create(info=dict(templates=[self.tmpl]))
        project_info = dict(volume_id=volume_id, template_id=tmpl_id)
        project = ProjectFactory.create(category=self.category,
                                        info=project_info)
        tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

        expected_data = []
        for i, task in enumerate(tasks):
            TaskRunFactory.create(task=task, project=project)
            (anno, tag, value,
             source) = self.anno_fixtures.create_describing_anno(i)
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[anno])
            self.result_repo.update(result)
            expected_data.append(anno)

        data = self.volume_exporter._get_data('describing', volume_id)
        assert_equal(data, expected_data)

    @with_context
    def test_get_csv_data_with_multiple_annotations(self):
        """Test get CSV data with multiple annotations."""
        self.category.info = {
            'volumes': self.volumes
        }
        self.project_repo.update_category(self.category)
        volume_id = self.volumes[0]['id']
        tmpl_id = self.tmpl['id']
        UserFactory.create(info=dict(templates=[self.tmpl]))
        project_info = dict(volume_id=volume_id, template_id=tmpl_id)
        project = ProjectFactory.create(category=self.category,
                                        info=project_info)
        tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

        expected_data = []
        for i, task in enumerate(tasks):
            TaskRunFactory.create(task=task, project=project)
            (anno, tag, value,
             source) = self.anno_fixtures.create_describing_anno(i)
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[anno])
            self.result_repo.update(result)
            header = "{} | {}".format(self.tmpl['project']['name'], tag)
            expected_data.append({
                'target': source, header: value
            })

        # Ensure same keys exist in all rows
        keys_lists = [row.keys() for row in expected_data]
        keys = list(set(itertools.chain(*keys_lists)))
        for row in expected_data:
            for key in keys:
                row[key] = row.get(key, None)

        data = self.volume_exporter._get_data('describing', volume_id,
                                              flat=True)
        expected_data = sorted(expected_data, key=lambda x: x['target'])
        assert_equal(data, expected_data)
