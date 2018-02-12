# -*- coding: utf8 -*-
"""Test volume exporter."""

import uuid
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
        self.iiif_volumes = [
            {
                'id': str(uuid.uuid4()),
                'name': 'A Volume',
                'short_name': 'a_volume',
                'source': 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
            }
        ]

    @with_context
    def test_transcription_data_with_one_project(self):
        """Test data with one project and one type of transcription."""
        self.category.info = {
            'volumes': self.iiif_volumes
        }
        self.project_repo.update_category(self.category)
        volume_id = self.iiif_volumes[0]['id']
        tmpl_id = self.tmpl['id']
        UserFactory.create(info=dict(templates=[self.tmpl]))
        project_info = dict(volume_id=volume_id, template_id=tmpl_id)
        project = ProjectFactory.create(category=self.category,
                                        info=project_info)
        tasks = TaskFactory.create_batch(3, project=project, n_answers=1)
        expected_data = []

        for i, task in enumerate(tasks):
            TaskRunFactory.create(task=task, project=project)
            (annotations, tag, value,
             source) = self.anno_fixtures.create_describing_anno(i)
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[annotations])
            self.result_repo.update(result)

        data = self.volume_exporter._get_data('describing', volume_id)
        expected_data = {tmpl_id: []}
        for i, task in enumerate(tasks):
            (annotations, tag, value,
             source) = self.anno_fixtures.create_describing_anno(i)
            expected_data[tmpl_id].append({
                'task_id': task.id,
                'parent_task_id': None,
                'target': source,
                'simple_data': {tag: value},
                'full_data': [annotations]
            })
        assert_dict_equal(data, expected_data)
