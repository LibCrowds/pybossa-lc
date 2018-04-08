# -*- coding: utf8 -*-
"""Test projects API."""

import json
from mock import patch, call
from nose.tools import *
from helper import web
from default import with_context, db, Fixtures
from factories import ProjectFactory, CategoryFactory
from factories import TaskFactory, TaskRunFactory
from pybossa.jobs import import_tasks
from pybossa.core import task_repo, result_repo, project_repo, user_repo
from pybossa.repositories import UserRepository

from pybossa_lc.api import projects as projects_api
from ..fixtures import TemplateFixtures


class TestProjectsApi(web.Helper):

    def setUp(self):
        super(TestProjectsApi, self).setUp()
        self.manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
        flickr_url = 'http://www.flickr.com/photos/132066275@N04/albums/'
        self.flickr_album_id = '12345'

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
    def test_task_import_direct_for_small_sets(self, mock_count, mock_create):
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
    @patch('pybossa_lc.api.projects.importer')
    def test_project_created_with_correct_details(self, mock_importer):
        """Test that a project is created with the correct details."""
        self.register(name=Fixtures.name)
        self.signin()
        vol = dict(id='123abc', name='My Volume')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        category.info = dict(presenter='iiif-annotation', volumes=[vol],
                             templates=[tmpl.to_dict()])
        project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'])
        res = self.app_post_json(endpoint, data=form_data)
        project = project_repo.get(1)

        # Check project details
        assert_equal(project.name, form_data['name'])
        assert_equal(project.short_name, form_data['short_name'])
        assert_equal(project.webhook, 'http://localhost/lc/analysis')
        assert_equal(project.published, True)
        assert_equal(project.description, tmpl.description)
        assert_equal(project.category_id, tmpl.category_id)
        assert_dict_equal(project.info, {
            'template_id': tmpl.id,
            'volume_id': vol['id']
        })

    @with_context
    @patch('pybossa_lc.api.projects.task_repo.update_tasks_redundancy')
    @patch('pybossa_lc.api.projects.importer')
    def test_new_project_task_redundancy_updated(self, mock_importer,
                                                 mock_update_redundancy):
        """Test task redundancy updated for new projects."""
        self.register(name=Fixtures.name)
        self.signin()
        min_answers = 10
        vol = dict(id='123abc', name='My Volume')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        tmpl.min_answers = min_answers
        category.info = dict(presenter='iiif-annotation', volumes=[vol],
                             templates=[tmpl.to_dict()])
        project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'])
        self.app_post_json(endpoint, data=form_data)
        project = project_repo.get(1)
        mock_update_redundancy.assert_called_once_with(project, min_answers)

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
        self.register()
        self.signin()
        vol = dict(id='123abc', name='My Volume', importer='iiif',
                   data=dict(manifest_uri=self.manifest_uri))
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        category.info = dict(presenter='iiif-annotation', volumes=[vol],
                             templates=[tmpl.to_dict()])
        project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'])
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'The project was generated with 1 task.'
        assert_equal(res_data['flash'], msg)
        project = project_repo.get(1)

        # Check correct task data imported
        expected = call(task_repo, project.id, type='iiif',
                        manifest_uri=self.manifest_uri)
        assert_equal(mock_importer.create_tasks.call_args_list, [expected])

    @with_context
    @patch('pybossa_lc.api.projects.importer')
    def test_z3950_project_creation(self, mock_importer):
        """Test that a Z39.50 project is created."""
        mock_importer.count_tasks_to_import.return_value = 1
        self.register()
        self.signin()
        vol = dict(id='123abc', name='My Volume', importer='z3950',
                   data=dict(album_id=self.flickr_album_id))
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        z3950_task = tmpl_fixtures.z3950_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=z3950_task)
        category.info = dict(presenter='z3950', volumes=[vol],
                             templates=[tmpl.to_dict()])
        project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'])
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'The project was generated with 1 task.'
        assert_equal(res_data['flash'], msg)
        project = project_repo.get(1)

        # Check correct task data imported
        expected = call(task_repo, project.id, type='z3950',
                        album_id=self.flickr_album_id)
        assert_equal(mock_importer.create_tasks.call_args_list, [expected])

    @with_context
    @patch('pybossa_lc.api.projects.importer')
    def test_project_created_with_volume_avatar(self, mock_importer):
        """Test that a project is created with the volume's avatar."""
        self.register()
        self.signin()
        vol = dict(id='123abc', name='My Volume', container='foo',
                   thumbnail='bar.png', thumbnail_url='/foo/bar.png')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        category.info = dict(presenter='iiif-annotation', volumes=[vol],
                             templates=[tmpl.to_dict()])
        project_repo.update_category(category)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=tmpl.id,
                         volume_id=vol['id'])
        res = self.app_post_json(endpoint, data=form_data)
        project = project_repo.get(1)

        # Check project avatar details
        assert_equal(project.info['container'], vol['container'])
        assert_equal(project.info['thumbnail'], vol['thumbnail'])
        assert_equal(project.info['thumbnail_url'], vol['thumbnail_url'])

    @with_context
    def test_unbuilt_volumes_returned_with_templates(self):
        """Test that only available volumes are returned with templates."""
        self.register()
        self.signin()
        user = user_repo.get(1)
        vol1 = dict(id='123abc', name='My Volume')
        vol2 = dict(id='456def', name='My Other Volume')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        tmpl1 = tmpl_fixtures.create_template(task_tmpl=select_task)
        tmpl2 = tmpl_fixtures.create_template(task_tmpl=select_task)

        # Incomplete template to be ignored
        tmpl3 = tmpl_fixtures.create_template()

        category.info = dict(presenter='iiif-annotation',
                             volumes=[vol1, vol2],
                             templates=[
                                 tmpl1.to_dict(),
                                 tmpl2.to_dict(),
                                 tmpl3.to_dict()
                             ])
        project_repo.update_category(category)

        # Leave one volume available for tmpl1
        ProjectFactory(owner=user, category=category,
                       info=dict(template_id=tmpl1.id, volume_id=vol1['id']))

        # Leave no volumes available for tmpl2
        ProjectFactory(owner=user, category=category,
                       info=dict(template_id=tmpl2.id, volume_id=vol1['id']))
        ProjectFactory(owner=user, category=category,
                       info=dict(template_id=tmpl2.id, volume_id=vol2['id']))

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        res = self.app_get_json(endpoint)
        res_data = json.loads(res.data)
        templates = res_data['templates']

        res_tmpl1 = next((t for t in templates if t['id'] == tmpl1.id), None)
        res_tmpl2 = next((t for t in templates if t['id'] == tmpl2.id), None)
        assert_equal([res_tmpl1['id'], res_tmpl2['id']], [tmpl1.id, tmpl2.id])

        assert_equal(res_tmpl1['available_volumes'], [vol2['id']])
        assert_equal(res_tmpl2['available_volumes'], [])

    @with_context
    def test_child_projects_not_built_from_non_iiif_templates(self):
        """Test that only IIIF projects can be built from parents."""
        self.register()
        user = user_repo.get(1)
        vol = dict(id='123abc', name='My Volume', importer='foo')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        parent_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl.parent_template_id = parent_tmpl.id

        category.info = dict(presenter='iiif-annotation',
                             volumes=[vol],
                             templates=[parent_tmpl.to_dict(),
                                        child_tmpl.to_dict()])
        project_repo.update_category(category)
        parent = ProjectFactory(owner=user, category=category,
                                info=dict(template_id=parent_tmpl.id,
                                          volume_id=vol['id']))

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=child_tmpl.id,
                         volume_id=vol['id'])
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'Only IIIF projects can be built from parents.'
        assert_equal(res_data['flash'], msg)

    @with_context
    def test_child_projects_not_built_from_incomplete_parents(self):
        """Test that child projects are not built from incomplete parents."""
        self.register()
        user = user_repo.get(1)
        vol = dict(id='123abc', name='My Volume', importer='iiif')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        parent_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl.parent_template_id = parent_tmpl.id

        category.info = dict(presenter='iiif-annotation',
                             volumes=[vol],
                             templates=[parent_tmpl.to_dict(),
                                        child_tmpl.to_dict()])
        project_repo.update_category(category)

        parent = ProjectFactory(owner=user, category=category,
                                info=dict(template_id=parent_tmpl.id,
                                          volume_id=vol['id']))

        n_tasks = 3
        tasks = TaskFactory.create_batch(n_tasks, n_answers=1, project=parent)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=child_tmpl.id,
                         volume_id=vol['id'])

        # Check parent with incomplete tasks and results
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'There is no valid parent for this template and volume.'
        assert_equal(res_data['flash'], msg)

        # Check parent with incomplete results
        for task in tasks:
            TaskRunFactory.create(user=user, project=parent, task=task)
        res = self.app_post_json(endpoint, data=form_data)
        res_data = json.loads(res.data)
        msg = 'There is no valid parent for this template and volume.'
        assert_equal(res_data['flash'], msg)

    @with_context
    @patch('pybossa.core.importer.create_tasks')
    @patch('pybossa.core.importer.count_tasks_to_import', return_value=1)
    def test_project_built_from_valid_parent_template(self, mock_count,
                                                      mock_create_tasks):
        """Test that child project built from parent."""
        self.register()
        user = user_repo.get(1)
        vol = dict(id='123abc', name='My Volume', importer='iiif')
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        select_task = tmpl_fixtures.iiif_select_tmpl
        parent_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl = tmpl_fixtures.create_template(task_tmpl=select_task)
        child_tmpl.parent_template_id = parent_tmpl.id

        category.info = dict(presenter='iiif-annotation',
                             volumes=[vol],
                             templates=[parent_tmpl.to_dict(),
                                        child_tmpl.to_dict()])
        project_repo.update_category(category)

        parent = ProjectFactory(id=42, owner=user, category=category,
                                info=dict(template_id=parent_tmpl.id,
                                          volume_id=vol['id']))

        n_tasks = 3
        tasks = TaskFactory.create_batch(n_tasks, n_answers=1, project=parent)
        for task in tasks:
            TaskRunFactory.create(user=user, project=parent, task=task)
        results = result_repo.filter_by(project_id=parent.id)
        for result in results:
            result.info = 'foo'
            result_repo.update(result)

        endpoint = '/lc/projects/{}/new'.format(category.short_name)
        form_data = dict(name='foo',
                         short_name='bar',
                         template_id=child_tmpl.id,
                         volume_id=vol['id'])

        self.app_post_json(endpoint, data=form_data)

        url_base = 'http://localhost/lc/projects/{0}/parent/iiif/{1}'
        parent_manifest_uri = url_base.format(category.short_name, parent.id)
        expected_call = call(task_repo, 1, type='iiif',
                             manifest_uri=parent_manifest_uri)
        assert_equal(mock_create_tasks.call_args_list, [expected_call])
