# -*- coding: utf8 -*-
"""Test volume exporter."""

import uuid
from nose.tools import *
from default import Test, db, with_context
from factories import CategoryFactory, ProjectFactory, TaskFactory
from factories import TaskRunFactory
from pybossa.repositories import ResultRepository, ProjectRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.exporters import VolumeExporter

class TestVolumeExporter(Test):

    def setUp(self):
        super(TestVolumeExporter, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)
        self.volume_exporter = VolumeExporter()
        self.category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(self.category)
        task_tmpl = tmpl_fixtures.iiif_transcribe_tmpl
        self.tmpl = tmpl_fixtures.create_template(task_tmpl=task_tmpl)
        self.export_formats = [
            {
                'id': '123',
                'fields': [
                    {
                        'header': 'Dynamic Field Header',
                        'template_id': self.tmpl['id'],
                        'value': ''
                    },
                    {
                        'header': 'Static Field Header',
                        'template_id': None,
                        'value': 'some value'
                    }
                ],
                'reference_header': 'ref',
                'name': 'MARC Template',
                'short_name': 'marc_template'
            }
        ]
        self.iiif_volumes = [
            {
                'id': str(uuid.uuid4()),
                'name': 'A Volume',
                'short_name': 'a_volume',
                'source': 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
            }
        ]
        self.category.info = {
            'export_formats': self.export_formats,
            'volumes': self.iiif_volumes
        }
        self.project_repo.update_category(self.category)

    @with_context
    def test_get_data_with_one_project(self):
        """Test the correct table is returned with simple data.

        That is, just one project and one type of transcription.
        """
        export_id = self.export_formats[0]['id']
        volume_id = self.iiif_volumes[0]['id']
        tmpl_id = self.tmpl['id']
        project_info = dict(volume_id=volume_id, template_id=tmpl_id)
        project = ProjectFactory.create(category=self.category,
                                        info=project_info)
        tasks = TaskFactory.create_batch(3, project=project, n_answers=1)
        expected_data = []

        for i, task in enumerate(tasks):
            TaskRunFactory.create(task=task, project=project)
            value = "Some Title {}".format(i)
            source = "http://example.org/iiif/book1/canvas/p{}".format(i)
            anno = {
                "body": [
                    {
                        "type": "TextualBody",
                        "purpose": "describing",
                        "value": value,
                        "format": "text/plain"
                    },
                    {
                        "type": "TextualBody",
                        "purpose": "tagging",
                        "value": "title"
                    }
                ],
                "target": {
                    "source": source,
                    "selector": {
                        "conformsTo": "http://www.w3.org/TR/media-frags/",
                        "type": "FragmentSelector",
                        "value": "?xywh=100,100,100,100"
                    }
                },
            }
            result = self.result_repo.get_by(task_id=task.id)
            result.info = dict(annotations=[anno])
            self.result_repo.update(result)
            row = {
                self.export_formats[0]['reference_header']: source
            }
            expected_data.append(row)

        data = self.volume_exporter._get_data(export_id, volume_id)
        assert_equal(data, expected_data)
