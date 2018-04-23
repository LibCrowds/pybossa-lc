# -*- coding: utf8 -*-
"""Test volume exporter."""

import uuid
import itertools
from flatten_json import flatten
from nose.tools import *
from default import Test, db, with_context
from factories import CategoryFactory, ProjectFactory, TaskFactory
from factories import TaskRunFactory, UserFactory
from pybossa.repositories import ResultRepository, ProjectRepository

from ..fixtures import TemplateFixtures, AnnotationFixtures
from pybossa_lc.exporters.base import CustomExporterBase


class TestCustomExporterBase(Test):

    def setUp(self):
        super(TestCustomExporterBase, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)
        self.exporter_base = CustomExporterBase()
        self.category = CategoryFactory()
        self.tmpl_fixtures = TemplateFixtures(self.category)
        self.anno_fixtures = AnnotationFixtures()

    def test_get_export_format(self):
        """Test correct export format returned."""
        tmpl = self.tmpl_fixtures.create_template()
        export_formats = [
            {
                'id': 123,
                'name': 'All',
                'short_name': 'all',
                'root_template_id': None
            },
            {
                'id': 456,
                'name': 'All',
                'short_name': 'all',
                'root_template_id': tmpl.id
            }
        ]
        self.category.info['export_formats'] = export_formats
        self.project_repo.update_category(self.category)

        _id = export_formats[1]['id']
        export_fmt = self.exporter_base._get_export_format(self.category, _id)
        assert_equal(export_fmt, export_formats[1])

    def test_get_template(self):
        """Test correct template returned."""
        tmpl1 = self.tmpl_fixtures.create_template()
        tmpl2 = self.tmpl_fixtures.create_template()
        templates = [tmpl1.to_dict(), tmpl2.to_dict()]
        self.category.info['templates'] = templates
        self.project_repo.update_category(self.category)

        ret_tmpl = self.exporter_base._get_template(self.category, tmpl2.id)
        assert_equal(ret_tmpl, tmpl2.to_dict())

    # @with_context
    # def test_get_json_data_with_one_project(self):
    #     """Test JSON data with one project and one type of transcription."""
    #     self.category.info = {
    #         'volumes': self.volumes
    #     }
    #     self.project_repo.update_category(self.category)
    #     volume_id = self.volumes[0]['id']
    #     task_tmpl = self.tmpl_fixtures.iiif_transcribe_tmpl
    #     tmpl = self.tmpl_fixtures.create_template(task_tmpl=task_tmpl)

    #     UserFactory.create(info=dict(templates=[tmpl.to_dict()]))
    #     project_info = dict(volume_id=volume_id, template_id=tmpl.id)
    #     project = ProjectFactory.create(category=self.category,
    #                                     info=project_info)
    #     tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

    #     expected_data = []
    #     for i, task in enumerate(tasks):
    #         TaskRunFactory.create(task=task, project=project)
    #         (annotation, tag, value,
    #          source) = self.anno_fixtures.create(i, 'describing')
    #         result = self.result_repo.get_by(task_id=task.id)
    #         result.info = dict(annotations=[annotation])
    #         self.result_repo.update(result)
    #         expected_data.append(annotation)

    #     data = self.volume_exporter_base._get_data('describing', volume_id)
    #     assert_equal(data, expected_data)

    # @with_context
    # def test_get_json_data_with_multiple_annotations(self):
    #     """Test get JSON data with multiple annotations."""
    #     task_tmpl = self.tmpl_fixtures.iiif_transcribe_tmpl
    #     tmpl = self.tmpl_fixtures.create_template(task_tmpl=task_tmpl)
    #     self.category.info = dict(volumes=self.volumes,
    #                               templates=[tmpl.to_dict()])
    #     self.project_repo.update_category(self.category)
    #     volume_id = self.volumes[0]['id']

    #     project_info = dict(volume_id=volume_id, template_id=tmpl.id)
    #     project = ProjectFactory.create(category=self.category,
    #                                     info=project_info)
    #     tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

    #     expected_data = []
    #     for i, task in enumerate(tasks):
    #         TaskRunFactory.create(task=task, project=project)
    #         (anno, tag, value,
    #          source) = self.anno_fixtures.create(i, 'describing')
    #         result = self.result_repo.get_by(task_id=task.id)
    #         result.info = dict(annotations=[anno])
    #         self.result_repo.update(result)
    #         expected_data.append(anno)

    #     data = self.volume_exporter_base._get_data('describing', volume_id)
    #     assert_equal(data, expected_data)

    # @with_context
    # def test_get_csv_data_with_multiple_annotations(self):
    #     """Test get CSV data with multiple annotations."""
    #     task_tmpl = self.tmpl_fixtures.iiif_transcribe_tmpl
    #     tmpl = self.tmpl_fixtures.create_template(task_tmpl=task_tmpl)
    #     self.category.info = dict(volumes=self.volumes,
    #                               templates=[tmpl.to_dict()])
    #     self.project_repo.update_category(self.category)
    #     volume_id = self.volumes[0]['id']

    #     project_info = dict(volume_id=volume_id, template_id=tmpl.id)
    #     project = ProjectFactory.create(category=self.category,
    #                                     info=project_info)
    #     tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

    #     expected_data = []
    #     for i, task in enumerate(tasks):
    #         TaskRunFactory.create(task=task, project=project)
    #         (anno, tag, value,
    #          source) = self.anno_fixtures.create(i, 'describing')
    #         result = self.result_repo.get_by(task_id=task.id)
    #         result.info = dict(annotations=[anno])
    #         self.result_repo.update(result)
    #         expected_row = dict(target=source)
    #         expected_row.update(flatten({
    #             tmpl.name: {
    #                 tag: [value]
    #             },
    #             'task_state': 'completed',
    #             'link': [None]
    #         }))
    #         expected_data.append(expected_row)

    #     expected_data = sorted(expected_data, key=lambda x: x['target'])
    #     data = self.volume_exporter_base._get_data('describing', volume_id,
    #                                                flat=True)
    #     assert_equal(data, expected_data)

    # @with_context
    # def test_get_csv_data_with_same_tags_for_the_same_target(self):
    #     """Test get CSV data with multiple tags for the same tags."""
    #     task_tmpl = self.tmpl_fixtures.iiif_transcribe_tmpl
    #     tmpl = self.tmpl_fixtures.create_template(task_tmpl=task_tmpl)
    #     self.category.info = dict(volumes=self.volumes,
    #                               templates=[tmpl.to_dict()])
    #     self.project_repo.update_category(self.category)
    #     volume_id = self.volumes[0]['id']

    #     project_info = dict(volume_id=volume_id, template_id=tmpl.id)
    #     project = ProjectFactory.create(category=self.category,
    #                                     info=project_info)
    #     tasks = TaskFactory.create_batch(3, project=project, n_answers=1)

    #     tag_values = []
    #     target = "example.com"
    #     for i, task in enumerate(tasks):
    #         TaskRunFactory.create(task=task, project=project)
    #         (anno, tag, value,
    #          source) = self.anno_fixtures.create(i, 'describing', tag="foo",
    #                                              target=target)
    #         result = self.result_repo.get_by(task_id=task.id)
    #         result.info = dict(annotations=[anno])
    #         self.result_repo.update(result)
    #         tag_values.append(value)

    #     expected_row = dict(target=target)
    #     expected_row.update(flatten({
    #         tmpl.name: {
    #             'foo': tag_values
    #         },
    #         'task_state': 'completed',
    #         'link': [None]
    #     }))
    #     expected_data = [expected_row]
    #     expected_data = sorted(expected_data, key=lambda x: x['target'])
    #     data = self.volume_exporter_base._get_data('describing', volume_id,
    #                                                flat=True)
    #     assert_equal(data, expected_data)

    # @with_context
    # def test_get_csv_data_with_links(self):
    #     """Test get CSV data with links."""
    #     self.category.info = {
    #         'volumes': self.volumes
    #     }
    #     self.project_repo.update_category(self.category)
    #     volume_id = self.volumes[0]['id']
    #     select_tmpl = self.tmpl_fixtures.iiif_select_tmpl
    #     transcribe_tmpl = self.tmpl_fixtures.iiif_transcribe_tmpl
    #     tmpl1 = self.tmpl_fixtures.create_template(task_tmpl=select_tmpl)
    #     tmpl2 = self.tmpl_fixtures.create_template(task_tmpl=transcribe_tmpl)
    #     tmpl3 = self.tmpl_fixtures.create_template(task_tmpl=transcribe_tmpl)

    #     UserFactory.create(info=dict(templates=[tmpl1, tmpl2, tmpl3]))
    #     parent_info = dict(volume_id=volume_id, template_id=tmpl1['id'])
    #     parent_project = ProjectFactory.create(category=self.category,
    #                                            info=parent_info)
    #     child_info1 = dict(volume_id=volume_id, template_id=tmpl2['id'])
    #     child_project1 = ProjectFactory.create(category=self.category,
    #                                            info=child_info1)
    #     child_info2 = dict(volume_id=volume_id, template_id=tmpl3['id'])
    #     child_project2 = ProjectFactory.create(category=self.category,
    #                                            info=child_info2)

    #     parent_tasks = TaskFactory.create_batch(1, project=parent_project,
    #                                             n_answers=1)
    #     parent_task_id = parent_tasks[0].id
    #     task_info = dict(parent_task_id=parent_task_id)
    #     child_tasks1 = TaskFactory.create_batch(3, project=child_project1,
    #                                             n_answers=1, info=task_info)
    #     child_tasks2 = TaskFactory.create_batch(3, project=child_project2,
    #                                             n_answers=1, info=task_info)

    #     expected_data = []
    #     results_data = {}
    #     target = "example.com"

    #     def create_task_runs(motivation, annotag, project, tasks):
    #         tag_values = []
    #         for i, task in enumerate(tasks):
    #             TaskRunFactory.create(task=task, project=project)
    #             (anno, tag, value,
    #              source) = self.anno_fixtures.create(motivation,
    #                                                  target=target,
    #                                                  tag=annotag)
    #             result = self.result_repo.get_by(task_id=task.id)
    #             result.info = dict(annotations=[anno])
    #             self.result_repo.update(result)
    #             if motivation == 'describing':
    #                 tag_values.append(value)

    #         results_data[annotag] = tag_values

    #     create_task_runs('tagging', 'title', parent_project, parent_tasks)
    #     create_task_runs('describing', 'title', child_project1, child_tasks1)
    #     create_task_runs('describing', 'genre', child_project2, child_tasks2)

    #     results_data['target'] = target
    #     expected_data = [flatten(results_data)]

    #     # Ensure same keys exist in all rows
    #     keys_lists = [row.keys() for row in expected_data]
    #     keys = list(set(itertools.chain(*keys_lists)))
    #     for row in expected_data:
    #         for key in keys:
    #             row[key] = row.get(key, None)

    #     data = self.volume_exporter._get_data('describing', volume_id,
    #                                           flat=True)
    #     expected_data = sorted(expected_data, key=lambda x: x['target'])
    #     assert_equal(data, expected_data)
