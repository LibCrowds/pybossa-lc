# -*- coding: utf8 -*-
"""Test user API."""

import json
from nose.tools import *
from helper import web
from default import with_context, db, Fixtures
from factories import CategoryFactory
from pybossa.repositories import UserRepository, ProjectRepository

from ..fixtures import TemplateFixtures


class TestUserApi(web.Helper):

    def setUp(self):
        super(TestUserApi, self).setUp()
        self.category = CategoryFactory()
        self.tmpl_fixtures = TemplateFixtures(self.category)
        self.user_repo = UserRepository(db)
        self.project_repo = ProjectRepository(db)

    @with_context
    def test_users_templates_listed(self):
        """Test user's templates are listed."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        user = self.user_repo.get_by_name(Fixtures.name)
        tmpl = self.tmpl_fixtures.create_template()
        user.info['templates'] = [tmpl.to_dict()]
        self.user_repo.update(user)
        endpoint = '/lc/users/{}/templates'.format(Fixtures.name)
        res = self.app_get_json(endpoint)
        data = json.loads(res.data)
        assert_equal(data['templates'], [tmpl.to_dict()])

    @with_context
    def test_add_template(self):
        """Test that a template is added."""
        self.register(email=Fixtures.email_addr, name=Fixtures.name,
                      password=Fixtures.password)
        self.signin(email=Fixtures.email_addr, password=Fixtures.password)
        template = self.tmpl_fixtures.create_template()
        endpoint = '/lc/users/{}/templates'.format(Fixtures.name)
        res = self.app_post_json(endpoint, data=template.to_dict())
        data = json.loads(res.data)
        updated_user = self.user_repo.get_by_name(Fixtures.name)
        templates = updated_user.info.get('templates')
        assert_equal(data['flash'], 'New template submitted for approval')
        assert_equal(len(templates), 1)
        tmpl_dict = template.to_dict()
        tmpl_dict['id'] = templates[0]['id']
        tmpl_dict['created'] = templates[0]['created']
        tmpl_dict['pending'] = True
        assert_dict_equal(templates[0], tmpl_dict)

        # Check redirect to update page
        next_url = '/lc/templates/{}/update'.format(templates[0]['id'])
        assert_equal(data['next'], next_url)
