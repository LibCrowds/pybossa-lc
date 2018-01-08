
# -*- coding: utf8 -*-
"""Test templates cache."""

from nose.tools import *
from default import Test, with_context, db
from factories import UserFactory, CategoryFactory
from pybossa.repositories import UserRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.cache import templates as templates_cache


class TestTemplatesCache(Test):

    def setUp(self):
        super(TestTemplatesCache, self).setUp()
        self.user_repo = UserRepository(db)
        self.category = CategoryFactory()
        self.tmpl_fixtures = TemplateFixtures(self.category)

    @with_context
    def test_all_templates_returned(self):
        """Test that all templates are returned."""
        tmpl1 = self.tmpl_fixtures.create_template()
        tmpl2 = self.tmpl_fixtures.create_template()
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        user1.info['templates'] = [tmpl1]
        user2.info['templates'] = [tmpl2]
        self.user_repo.update(user1)
        self.user_repo.update(user2)
        all_tmpls = templates_cache.get_all()
        assert_equal(all_tmpls, [tmpl1, tmpl2])

    @with_context
    def test_template_returned_by_id(self):
        """Test that a template is returned by ID."""
        tmpl1 = self.tmpl_fixtures.create_template()
        tmpl2 = self.tmpl_fixtures.create_template()
        user = UserFactory.create()
        user.info['templates'] = [tmpl1, tmpl2]
        self.user_repo.update(user)
        returned_tmpl = templates_cache.get_by_id(tmpl2['id'])
        assert_dict_equal(returned_tmpl, tmpl2)
