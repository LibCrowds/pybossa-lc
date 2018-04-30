# -*- coding: utf8 -*-
"""Test JSON Annotation exporter."""

from nose.tools import *
from mock import patch, call
from default import Test, db, with_context
from factories import CategoryFactory, ProjectFactory, TaskFactory
from factories import TaskRunFactory
from pybossa.repositories import ResultRepository

from ..fixtures.annotation import AnnotationFixtures
from pybossa_lc.exporters.json_anno_exporter import JsonAnnotationExporter


class TestJsonAnnotationExporter(Test):

    def setUp(self):
        super(TestJsonAnnotationExporter, self).setUp()
        self.result_repo = ResultRepository(db)

    def test_get_download_name(self):
        """Test JSON download name returned."""
        exporter = JsonAnnotationExporter()
        category = CategoryFactory(short_name='foo')
        motivation = 'bar'
        fmt = 'baz'
        dl_name = exporter.download_name(category, motivation)
        expected = '{0}_{1}_json.zip'.format(category.short_name, motivation)
        assert_equal(dl_name, expected)

    @with_context
    def test_get_response_data(self):
        """Test JSON Annotation data returned."""
        result_repo = ResultRepository(db)
        anno_fixtures = AnnotationFixtures()
        annotations = [anno_fixtures.create()] * 10
        category = CategoryFactory()
        project = ProjectFactory(category=category)
        task = TaskFactory(n_answers=1, project=project)
        TaskRunFactory.create(task=task, project=project)
        result = self.result_repo.get_by(task_id=task.id)
        anno_fixtures = AnnotationFixtures()
        motivation = 'describing'
        annotations = [anno_fixtures.create(motivation=motivation)] * 10
        result.info = dict(annotations=annotations)
        self.result_repo.update(result)

        exporter = JsonAnnotationExporter()
        data = exporter._respond_json(category, motivation)
        assert_equal(data, annotations)

    @patch('pybossa_lc.exporters.json_anno_exporter.JsonAnnotationExporter.'
           '_make_zip')
    def test_zips_pregenerated_for_all_motivations(self, mock_make_zip):
        """Test a JSON zip file is pregenerated for all motivations."""
        category = CategoryFactory()
        exporter = JsonAnnotationExporter()
        exporter.pregenerate_zip_files(category)
        assert_equal(len(mock_make_zip.call_args_list), 3)
        assert_in(call(category, 'describing'), mock_make_zip.call_args_list)
        assert_in(call(category, 'tagging'), mock_make_zip.call_args_list)
        assert_in(call(category, 'commenting'), mock_make_zip.call_args_list)
