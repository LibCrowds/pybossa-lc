# -*- coding: utf8 -*-
"""Test project template repo."""

from default import Test, db, with_context
from nose.tools import *
from factories import ProjectFactory, CategoryFactory, UserFactory
from pybossa.repositories import ProjectRepository
from pybossa.exc import WrongObjectError, DBIntegrityError

from ..fixtures import TemplateFixtures
from pybossa_lc.repositories.project_template import ProjectTemplateRepository

class TestProjectTemplateRepository(Test):

    def setUp(self):
        super(TestProjectTemplateRepository, self).setUp()
        self.project_repo = ProjectRepository(db)
        self.project_tmpl_repo = ProjectTemplateRepository(db)

    @with_context
    def test_get_returns_none_if_no_template(self):
        """Test get returns None if no template with the specified id."""
        fake_id = '123'
        tmpl = self.project_tmpl_repo.get(fake_id)
        assert_equal(tmpl, None)

    @with_context
    def test_get_returns_template(self):
        """Test get method returns a template if it exists."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)
        retrieved_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), retrieved_tmpl.to_dict())

    @with_context
    def test_get_approved_returns_none_if_no_approved_template(self):
        """Test get approved method returns None if template not approved."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)
        retrieved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_equal(retrieved_tmpl, None)

    @with_context
    def test_get_approved_returns_template(self):
        """Test get approved method returns a template if it exists"""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.pending = False
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        retrieved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), retrieved_tmpl.to_dict())

    @with_context
    def test_update(self):
        """Test template is updated."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)
        name = 'New Name'
        tmpl.name = name

        not_updated_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_not_equal(not_updated_tmpl.name, name)
        self.project_tmpl_repo.update(tmpl)

        not_updated_approved = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_not_equal(not_updated_approved, name)

        updated_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), updated_tmpl.to_dict())

    @with_context
    def test_update_approved(self):
        """Test approved template is updated."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        name = 'New Name'
        tmpl.name = name

        not_updated_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_not_equal(not_updated_tmpl.name, name)
        self.project_tmpl_repo.update(tmpl, True)

        not_updated_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_equal(not_updated_tmpl, None)

        updated_approved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), updated_approved_tmpl.to_dict())

    @with_context
    def test_save(self):
        """Test new templates are saved to the owner."""
        category = CategoryFactory()
        user = UserFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.owner_id = user.id

        not_saved_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_equal(not_saved_tmpl, None)
        self.project_tmpl_repo.save(tmpl)

        not_approved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_equal(not_approved_tmpl, None)

        saved_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), saved_tmpl.to_dict())

    @with_context
    def test_save_approved(self):
        """Test approved templates are saved to the category."""
        category = CategoryFactory()
        user = UserFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.owner_id = user.id

        not_saved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_equal(not_saved_tmpl, None)
        self.project_tmpl_repo.save(tmpl, True)

        approved_tmpl = self.project_tmpl_repo.get_approved(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), approved_tmpl.to_dict())

    @with_context
    def test_save_only_saves_templates(self):
        """Test save raises a WrongObjectError when not a template."""
        bad_object = dict()
        assert_raises(WrongObjectError, self.project_tmpl_repo.save,
                      bad_object)
