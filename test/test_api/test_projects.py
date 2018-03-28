# -*- coding: utf8 -*-
"""Test projects API."""

import json
from mock import patch
from nose.tools import *
from helper import web
from default import with_context, db, Fixtures
from factories import ProjectFactory, CategoryFactory
from pybossa.jobs import import_tasks
from pybossa.core import task_repo
from pybossa.repositories import ProjectRepository

from pybossa_lc.api import projects as projects_api
from ..fixtures import TemplateFixtures


class TestProjectsApi(web.Helper):

    def setUp(self):
        super(TestProjectsApi, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
        flickr_url = 'http://www.flickr.com/photos/132066275@N04/albums/'
        self.flickr_album_id = '12345'
        self.flickr_album_uri = '{}{}'.format(flickr_url, self.flickr_album_id)

    # @with_context
    # def test_get_valid_iiif_annotation_data(self):
    #     """Test the pattern for valid IIIF manifest URIs."""
    #     volume = {
    #         'name': 'some_manifest',
    #         'source': self.manifest_uri
    #     }
    #     parent_id = 123
    #     data = projects_api._get_iiif_annotation_data(volume, parent_id)
    #     expected = dict(type='iiif-annotation', manifest_uri=self.manifest_uri,
    #                     parent_id=parent_id)
    #     assert_equals(data, expected)

    @with_context
    def test_get_invalid_iiif_annotation_data(self):
        """Test the pattern for invalid IIIF manifest URIs."""
        manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/somethingelse'
        volume = {
            'name': 'some_manifest',
            'source': manifest_uri
        }
        template_id = 'foo'
        data = projects_api._get_iiif_annotation_data(volume, None)
        assert not data

    @with_context
    def test_get_valid_flickr_data(self):
        """Test the pattern for valid Flickr URIs."""
        volume = {
            'name': 'my_album',
            'source': self.flickr_album_uri
        }
        data = projects_api._get_flickr_data(volume)
        expected = dict(type='flickr', album_id=self.flickr_album_id)
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
    @patch('pybossa_lc.api.projects.enqueue_job')
    @patch('pybossa.core.importer.count_tasks_to_import')
    def test_task_import_queued_for_large_sets(self, mock_count, mock_enqueue):
        """Test that task imports are queued when over 300."""
        mock_count.return_value = 301
        project = ProjectFactory.create()
        import_data = dict(foo='bar')
        projects_api._import_tasks(project, **import_data)
        job = dict(name=projects_api.import_tasks,
                   args=[project.id],
                   kwargs=import_data,
                   timeout=self.flask_app.config.get('TIMEOUT'),
                   queue='medium')
        mock_enqueue.assert_called_with(job)

    @with_context
    @patch('pybossa.core.importer.create_tasks')
    @patch('pybossa.core.importer.count_tasks_to_import', return_value=300)
    def test_task_import_for_smaller_sets(self, mock_count, mock_create):
        """Test that task imports are created immediately when 300 or less."""
        project = ProjectFactory.create()
        data = dict(foo='bar')
        projects_api._import_tasks(project, **data)
        mock_create.assert_called_with(task_repo, project.id, **data)

    @with_context
    def test_project_creation_unauthorised_as_anon(self):
        """Test that a project is unauthorised for anonymous users."""
        category = CategoryFactory()
        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        res = self.app_post_json(endpoint)
        assert_equal(res.status_code, 401)

    @with_context
    def test_project_creation_fails_with_invalid_presenter(self):
        """Test that project creation fails with an invalid task presenter."""
        self.register()
        self.signin()
        category = CategoryFactory(info=dict(presenter='foo'))
        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        res = self.app_post_json(endpoint)
        res_data = json.loads(res.data)
        msg = 'Invalid task presenter, please contact an administrator'
        assert_equal(res_data['flash'], msg)

    @with_context
    @patch('pybossa_lc.api.projects.importer')
    def test_iiif_project_creation(self, mock_importer):
        """Test that a IIIF select project is created."""
        mock_importer.count_tasks_to_import.return_value = 1
        self.register(name=Fixtures.name)
        self.signin()
        vol = dict(id='123abc', name='My Volume', source=self.manifest_uri)
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        category.info = dict(presenter='iiif-annotation', volumes=[vol],
                             templates=[tmpl.to_dict()])
        self.project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'],
                         parent_id='None')
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'The project was generated with 1 task.'
        assert_equal(res_data['flash'], msg)
        project = self.project_repo.get(1)
        assert_equal(project.info['template_id'], tmpl.id)
        assert_equal(project.info['volume_id'], vol['id'])
        assert_equal(project.description, tmpl.description)
        assert_equal(project.category_id, tmpl.category_id)
        assert_equal(project.published, False)

    @with_context
    @patch('pybossa_lc.api.projects.importer')
    def test_z3950_project_creation(self, mock_importer):
        """Test that a Z39.50 project is created."""
        mock_importer.count_tasks_to_import.return_value = 1
        self.register(name=Fixtures.name)
        self.signin()
        vol = dict(id='123abc', name='My Volume', source=self.flickr_album_uri)
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        category.info = dict(presenter='z3950', volumes=[vol],
                             templates=[tmpl.to_dict()])
        self.project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'],
                         parent_id='None')
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'The project was generated with 1 task.'
        assert_equal(res_data['flash'], msg)
        project = self.project_repo.get(1)
        assert_equal(project.info['template_id'], tmpl.id)
        assert_equal(project.info['volume_id'], vol['id'])
        assert_equal(project.description, tmpl.description)
        assert_equal(project.category_id, tmpl.category_id)
        assert_equal(project.published, False)
