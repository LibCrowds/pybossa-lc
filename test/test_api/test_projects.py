# -*- coding: utf8 -*-
"""Test projects API."""

from mock import patch, MagicMock
from nose.tools import assert_equals
from helper import web
from default import with_context
from factories import ProjectFactory

from pybossa.jobs import import_tasks
from pybossa.core import task_repo
from pybossa_lc.api import projects as projects_api


class TestProjectsApi(web.Helper):

    def setUp(self):
        super(TestProjectsApi, self).setUp()

    @with_context
    def test_get_valid_iiif_annotation_data(self):
        """Test the pattern for valid IIIF manifest URIs."""
        manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
        volume = {
            'name': 'some_manifest',
            'source': manifest_uri
        }
        template_id = 'foo'
        parent_id = 123
        data = projects_api._get_iiif_annotation_data(volume, template_id,
                                                      parent_id)
        expected = dict(type='iiif-annotation', manifest_uri=manifest_uri,
                        template_id=template_id, parent_id=parent_id)
        assert_equals(data, expected)

    @with_context
    def test_get_invalid_iiif_annotation_data(self):
        """Test the pattern for invalid IIIF manifest URIs."""
        manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/somethingelse'
        volume = {
            'name': 'some_manifest',
            'source': manifest_uri
        }
        template_id = 'foo'
        data = projects_api._get_iiif_annotation_data(volume, template_id,
                                                      None)
        assert not data

    @with_context
    def test_get_valid_flickr_data(self):
        """Test the pattern for valid Flickr URIs."""
        album_id = '12345'
        base_url = 'http://www.flickr.com/photos/132066275@N04/albums/'
        album_uri = '{}{}'.format(base_url, album_id)
        volume = {
            'name': 'my_album',
            'source': album_uri
        }
        data = projects_api._get_flickr_data(volume)
        expected = dict(type='flickr', album_id=album_id)
        assert_equals(data, expected)

    @with_context
    def test_get_invalid_flickr_data(self):
        """Test the pattern for invalid Flickr URIs."""
        invalid_url = 'http://www.flickr.com/photos/132066275@N04'
        volume = {
            'name': 'my_album',
            'source': invalid_url
        }
        data = projects_api._get_flickr_data(volume)
        assert not data

    @with_context
    @patch('pybossa_lc.api.analysis.Queue.enqueue')
    @patch('pybossa.core.importer.count_tasks_to_import', return_value=301)
    def test_task_import_queued_for_large_sets(self, mock_count, mock_enqueue):
        """Test that task imports are queued when over 300."""
        project = ProjectFactory.create()
        data = dict(foo='bar')
        projects_api._import_tasks(project, **data)
        mock_enqueue.assert_called_with(import_tasks, project.id, **data)

    @with_context
    @patch('pybossa.core.importer.create_tasks')
    @patch('pybossa.core.importer.count_tasks_to_import', return_value=300)
    def test_task_import_for_smaller_sets(self, mock_count, mock_create):
        """Test that task imports are created immediately when 300 or less."""
        project = ProjectFactory.create()
        data = dict(foo='bar')
        projects_api._import_tasks(project, **data)
        mock_create.assert_called_with(task_repo, project.id, **data)