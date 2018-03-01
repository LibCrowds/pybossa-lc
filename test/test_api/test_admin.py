# -*- coding: utf8 -*-
"""Test admin API."""

import json
from mock import patch, call
from nose.tools import *
from helper import web
from default import with_context, db
from factories import CategoryFactory, UserFactory, ProjectFactory
from pybossa.repositories import ProjectRepository, UserRepository

from ..fixtures import TemplateFixtures


class TestAdminApi(web.Helper):

    def setUp(self):
        super(TestAdminApi, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)

    @with_context
    def test_get_pending_templates(self):
        """Test pending templates returned for all users."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl1 = tmpl_fixtures.create_template()
        tmpl2 = tmpl_fixtures.create_template()
        UserFactory.create(info=dict(templates=[tmpl1.to_dict()]))
        UserFactory.create(info=dict(templates=[tmpl2.to_dict()]))
        endpoint = '/lc/admin/templates/pending'
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        expected = [tmpl1.to_dict(), tmpl2.to_dict()]
        map(lambda x: x.pop('_original'), data['templates'])
        assert_equal(data['templates'], expected)

    @with_context
    def test_original_added_to_pending_templates(self):
        """Test original added to pending templates."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        new_name = 'foo'
        original_name = tmpl.name
        tmpl.name = new_name
        UserFactory.create(info=dict(templates=[tmpl.to_dict()]))
        tmpl.name = original_name
        endpoint = '/lc/admin/templates/pending'
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['templates'][0]['name'], new_name)
        assert_dict_equal(data['templates'][0]['_original'], tmpl.to_dict())

    @with_context
    @patch('pybossa_lc.api.admin.render_template', return_value=True)
    def test_template_approved(self, mock_render):
        """Test template approval."""
        self.register()
        self.signin()
        category = CategoryFactory()
        user = self.user_repo.get(1)
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.pending = True
        tmpl.owner_id = user.id
        user.info = dict(templates=[tmpl.to_dict()])
        self.user_repo.update(user)
        endpoint = '/lc/admin/templates/{}/approve'.format(tmpl.id)

        # Test CSRF returned with GET response
        get_res = self.app_get_json(endpoint)
        get_data = json.loads(get_res.data)
        assert_in('csrf', get_data.keys())

        # Test approved template added to category
        post_res = self.app_post_json(endpoint, data=get_data)
        post_data = json.loads(post_res.data)
        assert_equal(post_data['flash'], 'Template approved')
        updated_category = self.project_repo.get_category(category.id)
        category_templates = updated_category.info.get('templates')
        tmpl.pending = False
        assert_equal(category_templates, [tmpl.to_dict()])

        # Test user template no longer pending
        updated_user = self.user_repo.get(user.id)
        user_templates = updated_user.info.get('templates')
        assert_equal(user_templates, [tmpl.to_dict()])

    @with_context
    @patch('pybossa_lc.api.admin.render_template', return_value=True)
    def test_template_rejected(self, mock_render):
        """Test template rejection."""
        self.register()
        self.signin()
        category = CategoryFactory()
        user = self.user_repo.get(1)
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.pending = True
        tmpl.owner_id = user.id
        user.info = dict(templates=[tmpl.to_dict()])
        self.user_repo.update(user)
        endpoint = '/lc/admin/templates/{}/reject'.format(tmpl.id)

        # Test CSRF returned with GET response
        get_res = self.app_get_json(endpoint)
        get_data = json.loads(get_res.data)
        assert_in('csrf', get_data.keys())

        # Test approved template not added to category
        post_res = self.app_post_json(endpoint, data=get_data)
        post_data = json.loads(post_res.data)
        assert_equal(post_data['flash'], 'Email sent to template owner')
        updated_category = self.project_repo.get_category(category.id)
        category_templates = updated_category.info.get('templates')
        assert_equal(category_templates, None)

        # Test user template no longer pending
        updated_user = self.user_repo.get(user.id)
        user_templates = updated_user.info.get('templates')
        tmpl.pending = False
        assert_equal(user_templates, [tmpl.to_dict()])

    @with_context
    @patch('pybossa_lc.api.admin.analyse_all')
    @patch('pybossa_lc.api.admin.render_template', return_value=True)
    def test_results_updated_when_template_approved(self, mock_render,
                                                    mock_analyse_all):
        """Test results updated when template approved."""
        self.register()
        self.signin()
        presenter = 'foo'
        category = CategoryFactory(info=dict(presenter=presenter))
        user = self.user_repo.get(1)
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.pending = True
        tmpl.owner_id = user.id
        user.info = dict(templates=[tmpl.to_dict()])
        self.user_repo.update(user)
        projects = ProjectFactory.create_batch(3, owner=user,
                                               category=category,
                                               info=dict(template_id=tmpl.id))

        endpoint = '/lc/admin/templates/{}/approve'.format(tmpl.id)
        get_res = self.app_get_json(endpoint)
        get_data = json.loads(get_res.data)
        self.app_post_json(endpoint, data=get_data)
        expected_calls = [call(project.id, presenter) for project in projects]
        assert_equal(expected_calls, mock_analyse_all.call_args_list)
