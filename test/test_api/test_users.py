# -*- coding: utf8 -*-
"""Test category API."""

import json
import uuid
from mock import patch, MagicMock
from nose.tools import *
from helper import web
from default import with_context, db, Fixtures
from factories import CategoryFactory
from pybossa.repositories import UserRepository, ProjectRepository
from pybossa.jobs import import_tasks

from pybossa_lc.forms import *


class TestCategoryApi(web.Helper):

    def setUp(self):
        super(TestCategoryApi, self).setUp()
        self.user_repo = UserRepository(db)
        self.project_repo = ProjectRepository(db)
        field = dict(label='Title', type='input', inputType='text',
                     placeholder='', model='title')
        self.category = CategoryFactory.create()
        self.project_tmpl = dict(name='My Project Type', tutorial='Do stuff',
                                 description='This project is amazing',
                                 coowners=[], category_id=self.category.id)
        self.iiif_select_tmpl = dict(tag='title', mode='select',
                                     objective='Mark up', guidance='Do it now')
        self.iiif_transcribe_tmpl = dict(tag='title', mode='transcribe',
                                         objective='Transcribe the title',
                                         guidance='Do it now',
                                         fields_schema=[field])
        z3950_db = self.flask_app.config['Z3950_DATABASES'].keys()[0]
        self.z3950_tmpl = dict(database=z3950_db, institutions=['OCLC'])

    def create_template(self, task_tmpl=None):
        return dict(id=str(uuid.uuid4()), project=self.project_tmpl,
                    task=task_tmpl)

    @with_context
    def test_templates_listed_for_owner(self):
        """Test templates are listed for the owner."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.create_template()
        user.info['templates'] = [tmpl]
        self.user_repo.update(user)
        endpoint = '/libcrowds/users/{}/templates'.format(Fixtures.name)

        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['templates'], [tmpl])
        assert_equal(data['form']['errors'], {})

    @with_context
    def test_templates_listed_for_coowner(self):
        """Test templates are listed for the coowner."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.register(email=Fixtures.email_addr2, name=Fixtures.name2,
                      password=Fixtures.password)
        owner = self.user_repo.get_by_name(Fixtures.name)
        coowner = self.user_repo.get_by_name(Fixtures.name2)
        tmpl = self.create_template()
        tmpl['project']['coowners'] = [coowner.id]
        owner.info['templates'] = [tmpl]
        self.user_repo.update(owner)

        # Sign in as co-owner
        self.signin(email=coowner.email_addr, password=Fixtures.password)

        endpoint = '/libcrowds/users/{}/templates'.format(coowner.name)
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['templates'], [tmpl])
        assert_equal(data['form']['errors'], {})

    @with_context
    def test_get_template_for_owner(self):
        """Test get template by ID for owner."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        owner = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.create_template()
        owner.info['templates'] = [tmpl]
        self.user_repo.update(owner)

        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        endpoint = '/libcrowds/users/{}/templates/{}'.format(owner.name,
                                                             tmpl['id'])
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['template'], tmpl)

    @with_context
    def test_get_template_for_coowner(self):
        """Test get template by ID for co-owner."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.register(email=Fixtures.email_addr2, name=Fixtures.name2,
                      password=Fixtures.password)
        owner = self.user_repo.get_by_name(Fixtures.name)
        coowner = self.user_repo.get_by_name(Fixtures.name2)
        tmpl = self.create_template()
        tmpl['project']['coowners'] = [coowner.id]
        owner.info['templates'] = [tmpl]
        self.user_repo.update(owner)

        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        endpoint = '/libcrowds/users/{}/templates/{}'.format(coowner.name,
                                                             tmpl['id'])
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['template'], tmpl)

    @with_context
    def test_add_template(self):
        """Test that a template is added."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        endpoint = '/libcrowds/users/{}/templates'.format(Fixtures.name)
        res = self.app_post_json(endpoint, data=self.project_tmpl,
                                 follow_redirects=True)
        data = json.loads(res.data)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        templates = updated_user.info.get('templates')
        assert_equal(data['flash'], 'Project template created')
        assert_equal(len(templates), 1)
        tmpl_id = templates[0].pop('id')
        expected = dict(project=self.project_tmpl, task=None)
        assert_dict_equal(templates[0], expected)

        # Check redirect to update page
        next_url = '/libcrowds/users/{0}/templates/{1}'.format(Fixtures.name,
                                                               tmpl_id)
        assert_equal(data['next'], next_url)

    @with_context
    def test_add_iiif_transcribe_task(self):
        """Test a IIIF transcribe task is added to a template."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.create_template()
        user.info['templates'] = [tmpl]
        self.user_repo.update(user)

        self.category.info = dict(presenter='iiif-annotation')
        self.project_repo.update_category(self.category)

        url_base = '/libcrowds/users/{}/templates/{}/tasks'
        endpoint = url_base.format(Fixtures.name, tmpl['id'])

        res = self.app_post_json(endpoint, data=self.iiif_transcribe_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        tmpl['task'] = self.iiif_transcribe_tmpl
        assert_equal(json.loads(res.data)['flash'], 'Task template updated')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], tmpl)

    @with_context
    def test_add_task_template_for_coowner(self):
        """Test a task is added to a template for co-owner's."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.register(email=Fixtures.email_addr2, name=Fixtures.name2,
                      password=Fixtures.password)
        owner = self.user_repo.get_by_name(Fixtures.name)
        coowner = self.user_repo.get_by_name(Fixtures.name2)
        tmpl = self.create_template()
        tmpl['project']['coowners'] = [coowner.id]
        owner.info['templates'] = [tmpl]
        self.user_repo.update(owner)

        # Sign in as co-owner
        self.signin(email=coowner.email_addr, password=Fixtures.password)

        self.category.info = dict(presenter='iiif-annotation')
        self.project_repo.update_category(self.category)
        url_base = '/libcrowds/users/{}/templates/{}/tasks'
        endpoint = url_base.format(coowner.name, tmpl['id'])

        res = self.app_post_json(endpoint, data=self.iiif_transcribe_tmpl)
        print res.data
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        tmpl['task'] = self.iiif_transcribe_tmpl
        assert_equal(json.loads(res.data)['flash'], 'Task template updated')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], tmpl)

    @with_context
    def test_add_iiif_select_task(self):
        """Test a IIIF select task is added."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.create_template()
        user.info['templates'] = [tmpl]
        self.user_repo.update(user)

        self.category.info = dict(presenter='iiif-annotation')
        self.project_repo.update_category(self.category)

        url_base = '/libcrowds/users/{}/templates/{}/tasks'
        endpoint = url_base.format(Fixtures.name, tmpl['id'])

        res = self.app_post_json(endpoint, data=self.iiif_select_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        tmpl['task'] = self.iiif_select_tmpl
        assert_equal(json.loads(res.data)['flash'], 'Task template updated')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], tmpl)

    @with_context
    def test_add_z3950_task(self):
        """Test a Z39.50 task is added."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.create_template()
        user.info['templates'] = [tmpl]
        self.user_repo.update(user)

        self.category.info = dict(presenter='z3950')
        self.project_repo.update_category(self.category)

        url_base = '/libcrowds/users/{}/templates/{}/tasks'
        endpoint = url_base.format(Fixtures.name, tmpl['id'])

        res = self.app_post_json(endpoint, data=self.z3950_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        tmpl['task'] = self.z3950_tmpl
        assert_equal(json.loads(res.data)['flash'], 'Task template updated')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], tmpl)

    # @with_context
    # def test_update_template(self):
    #     """Test the update template endpoint."""
    #     info = dict(templates=[self.iiif_transcribe_tmpl])
    #     category = CategoryFactory.create(info=info)
    #     url_tmpl = '/libcrowds/users/{}/templates/{}'
    #     endpoint = url_tmpl.format(category.id,
    #                                self.iiif_transcribe_tmpl['id'])

    #     # Test anon user unauthorised
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 401)

    #     # Test non-admin forbidden
    #     self.register()
    #     self.signout()
    #     self.register(fullname="jane", name="jane", email="jane@jane.com")
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 403)

    #     # Test admin user authorised
    #     self.signin()
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 200)

    #     # Test redirects without a task presenter
    #     assert_equal(json.loads(res.data)['next'], "/admin/categories")
    #     category.info['presenter'] = 'iiif-annotation'
    #     self.project_repo.update_category(category)

    #     # Test form is populated
    #     form = json.loads(res.data)['form']
    #     form_fields = {k: v for k, v in form.items()
    #                    if k not in ['csrf', 'errors']}
    #     assert_dict_equal(form_fields, self.iiif_transcribe_tmpl)

    #     # Test that a template is updated
    #     self.iiif_transcribe_tmpl['name'] = 'A new name'
    #     res = self.app_post_json(endpoint, data=self.iiif_transcribe_tmpl)
    #     updated_category = self.project_repo.get_category(category.id)
    #     templates = updated_category.info.get('templates')
    #     assert_equal(json.loads(res.data)['flash'], 'Project template updated')
    #     assert_equal(len(templates), 1)
    #     assert_dict_equal(templates[0], self.iiif_transcribe_tmpl)

    # @with_context
    # def test_delete_template(self):
    #     """Test the delete template endpoint."""
    #     info = dict(templates=[self.iiif_transcribe_tmpl])
    #     category = CategoryFactory.create(info=info)
    #     url_tmpl = '/libcrowds/users/{}/templates/{}/delete'
    #     endpoint = url_tmpl.format(category.id,
    #                                self.iiif_transcribe_tmpl['id'])

    #     # Test anon user unauthorised
    #     res = self.app_post_json(endpoint)
    #     assert_equal(res.status_code, 401)

    #     # Test non-admin forbidden
    #     self.register()
    #     self.signout()
    #     self.register(fullname="jane", name="jane", email="jane@jane.com")
    #     res = self.app_post_json(endpoint)
    #     assert_equal(res.status_code, 403)

    #     # Test that a template is deleted for admin users
    #     self.register()
    #     self.signin()
    #     res = self.app_post_json(endpoint)
    #     updated_category = self.project_repo.get_category(category.id)
    #     assert_equal(json.loads(res.data)['flash'], 'Project template deleted')
    #     assert not updated_category.info.get('templates')
