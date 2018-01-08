# -*- coding: utf8 -*-
"""Test templates cache."""

from nose.tools import *
from default import Test, with_context, db
from factories import UserFactory
from pybossa.repositories import UserRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.cache import templates as templates_cache


class TestTemplatesCache(Test):

    def setUp(self):
        super(TestTemplatesCache, self).setUp()
        self.user_repo = UserRepository(db)

    @with_context
    def test_owners_templates_returned(self):
        """Test that an owner's templates are returned."""
        tmpl1 = TemplateFixtures.create_template()
        tmpl2 = TemplateFixtures.create_template()
        owner = UserFactory.create()
        other_user = UserFactory.create()
        owner.info['templates'] = [tmpl1]
        other_user.info['templates'] = [tmpl2]
        self.user_repo.update(owner)
        self.user_repo.update(other_user)
        owner_templates = templates_cache.get_all(owner.id)
        assert_dict_equal(owner_templates[0], tmpl1)

    @with_context
    def test_coowners_templates_returned(self):
        """Test that an co-owner's templates are returned."""
        tmpl1 = TemplateFixtures.create_template()
        tmpl2 = TemplateFixtures.create_template()
        owner = UserFactory.create()
        coowner = UserFactory.create()
        other_user = UserFactory.create()
        tmpl1['project']['coowners'] = [coowner.id]
        owner.info['templates'] = [tmpl1]
        other_user.info['templates'] = [tmpl2]
        self.user_repo.update(owner)
        self.user_repo.update(other_user)
        coowner_templates = templates_cache.get_all(coowner.id)
        assert_dict_equal(coowner_templates[0], tmpl1)

    @with_context
    def test_owners_template_returned_by_id(self):
        """Test that an owner's template is returned by ID."""
        tmpl1 = TemplateFixtures.create_template()
        tmpl2 = TemplateFixtures.create_template()
        tmpl3 = TemplateFixtures.create_template()
        owner = UserFactory.create()
        other_user = UserFactory.create()
        owner.info['templates'] = [tmpl1, tmpl3]
        other_user.info['templates'] = [tmpl2]
        self.user_repo.update(owner)
        self.user_repo.update(other_user)
        owner_template = templates_cache.get_by_id(owner.id, tmpl3['id'])
        assert_is_not_none(owner_template)
        assert_equal(owner_template, tmpl3)

    @with_context
    def test_coowners_template_returned_by_id(self):
        """Test that a co-owner's template is returned by ID."""
        tmpl1 = TemplateFixtures.create_template()
        tmpl2 = TemplateFixtures.create_template()
        tmpl3 = TemplateFixtures.create_template()
        owner = UserFactory.create()
        coowner = UserFactory.create()
        other_user = UserFactory.create()
        tmpl1['project']['coowners'] = [coowner.id]
        tmpl3['project']['coowners'] = [coowner.id]
        owner.info['templates'] = [tmpl1, tmpl3]
        other_user.info['templates'] = [tmpl2]
        self.user_repo.update(owner)
        self.user_repo.update(other_user)
        coowner_template = templates_cache.get_by_id(coowner.id, tmpl3['id'])
        assert_is_not_none(coowner_template)
        assert_equal(coowner_template, tmpl3)
