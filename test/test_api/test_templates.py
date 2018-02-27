# -*- coding: utf8 -*-
"""Test templates API."""

import json
from nose.tools import *
from helper import web
from default import with_context, db, Fixtures
from factories import CategoryFactory
from pybossa.repositories import UserRepository, ProjectRepository

from ..fixtures import TemplateFixtures


class TestTemplatesApi(web.Helper):

    def setUp(self):
        super(TestTemplatesApi, self).setUp()
        self.category = CategoryFactory()
        self.tmpl_fixtures = TemplateFixtures(self.category)
        self.user_repo = UserRepository(db)
        self.project_repo = ProjectRepository(db)

    def create_tmpl_with_context(self, name, presenter):
        """Create user template context."""
        self.register(email=Fixtures.email_addr, name=name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        template = self.tmpl_fixtures.create_template()
        template.pending = False
        user.info['templates'] = [template.to_dict()]
        self.user_repo.update(user)
        self.category.info = dict(presenter=presenter)
        self.project_repo.update_category(self.category)
        return template

    @with_context
    def test_update_template(self):
        """Test that project template is updated."""
        template = self.create_tmpl_with_context(Fixtures.name, 'z3950')
        endpoint = '/lc/templates/{}/update'.format(template.id)
        template.name = 'Some new name'
        res = self.app_post_json(endpoint, data=template.to_dict())
        data = json.loads(res.data)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        templates = updated_user.info.get('templates')
        template.pending = True
        assert_equal(data['flash'], 'Updates submitted for approval')
        assert_equal(len(templates), 1)
        assert_dict_equal(templates[0], template.to_dict())

    @with_context
    def test_add_iiif_transcribe_task(self):
        """Test a IIIF transcribe task is added to a template."""
        template = self.create_tmpl_with_context(Fixtures.name,
                                                 'iiif-annotation')
        endpoint = '/lc/templates/{}/task'.format(template.id)
        res = self.app_post_json(endpoint,
                                 data=self.tmpl_fixtures.iiif_transcribe_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        template.task = self.tmpl_fixtures.iiif_transcribe_tmpl
        template.pending = True
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Updates submitted for approval')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], template.to_dict())

    @with_context
    def test_add_iiif_select_task(self):
        """Test a IIIF select task is added."""
        template = self.create_tmpl_with_context(Fixtures.name,
                                                 'iiif-annotation')
        endpoint = '/lc/templates/{}/task'.format(template.id)
        res = self.app_post_json(endpoint,
                                 data=self.tmpl_fixtures.iiif_select_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        template.task = self.tmpl_fixtures.iiif_select_tmpl
        template.pending = True
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Updates submitted for approval')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], template.to_dict())

    @with_context
    def test_add_z3950_task(self):
        """Test a Z39.50 task is added."""
        template = self.create_tmpl_with_context(Fixtures.name, 'z3950')
        endpoint = '/lc/templates/{}/task'.format(template.id)
        res = self.app_post_json(endpoint, data=self.tmpl_fixtures.z3950_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        template.task = self.tmpl_fixtures.z3950_tmpl
        template.pending = True
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Updates submitted for approval')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], template.to_dict())

    @with_context
    def test_update_iiif_task_template(self):
        """Test a IIIF Annotation task template is updated."""
        template = self.create_tmpl_with_context(Fixtures.name,
                                                 'iiif-annotation')
        data = dict(objective='Foo', guidance='bar', tag='baz',
                    mode='transcribe', fields_schema=[])
        endpoint = '/lc/templates/{}/task'.format(template.id)
        res = self.app_post_json(endpoint, data=data)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        template.pending = True
        template.task = data
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Updates submitted for approval')
        assert_equal(len(user_templates), 1)
        assert_dict_equal(user_templates[0], template.to_dict())

    @with_context
    def test_analysis_rules_added(self):
        """Test analysis rules are added for IIIF templates."""
        template = self.create_tmpl_with_context(Fixtures.name, 'z3950')
        endpoint = '/lc/templates/{}/rules'.format(template.id)
        res = self.app_post_json(endpoint, data=self.tmpl_fixtures.rules_tmpl)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        template.pending = True
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Updates submitted for approval')
        assert_equal(len(user_templates), 1)
        assert_equal(user_templates[0]['rules'], self.tmpl_fixtures.rules_tmpl)

    @with_context
    def test_delete_template(self):
        """Test a template is deleted."""
        template = self.create_tmpl_with_context(Fixtures.name, 'foo')
        endpoint = '/lc/templates/{}/delete'.format(template.id)
        res = self.app_post_json(endpoint)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        flash_msg = json.loads(res.data)['flash']
        assert_equal(flash_msg, 'Template deleted')
        assert_equal(len(user_templates), 0)

    @with_context
    def test_delete_approved_template(self):
        """Test an approved template is not deleted."""
        template = self.create_tmpl_with_context(Fixtures.name, 'foo')
        self.category.info['templates'] = [template.to_dict()]
        self.project_repo.update_category(self.category)
        endpoint = '/lc/templates/{}/delete'.format(template.id)
        res = self.app_post_json(endpoint)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        user_templates = updated_user.info.get('templates')
        flash_msg = json.loads(res.data)['flash']
        msg = 'Approved templates can only be deleted by administrators'
        assert_equal(flash_msg, msg)
        assert_equal(user_templates, [template.to_dict()])
