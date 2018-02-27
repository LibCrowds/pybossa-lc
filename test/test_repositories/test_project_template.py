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
        """Test get returns None if no template."""
        fake_id = '123'
        tmpl = self.project_tmpl_repo.get(fake_id)
        assert_equal(tmpl, None)

    @with_context
    def test_get_pending_returns_none_if_no_template(self):
        """Test get pending returns None if no template."""
        fake_id = '123'
        tmpl = self.project_tmpl_repo.get_pending(fake_id)
        assert_equal(tmpl, None)

    @with_context
    def test_get_returns_template(self):
        """Test get returns a template if it exists."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        retrieved_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(retrieved_tmpl.to_dict(), tmpl.to_dict())

    @with_context
    def test_get_pending_returns_template(self):
        """Test get pending returns a template if it exists."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)
        retrieved_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_dict_equal(retrieved_tmpl.to_dict(), tmpl.to_dict())

    @with_context
    def test_get_all_returns_approved_templates(self):
        """Test get approved returns approved templates."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        approved_tmpl = tmpl_fixtures.create_template()
        pending_tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[pending_tmpl.to_dict()])
        UserFactory(info=user_info)
        category.info['templates'] = [approved_tmpl.to_dict()]
        self.project_repo.update_category(category)
        retrieved = [t.to_dict() for t in self.project_tmpl_repo.get_all()]
        expected = [approved_tmpl.to_dict()]
        assert_equal(retrieved, expected)

    @with_context
    def test_get_all_pending_returns_pending_templates(self):
        """Test get pending returns pending templates."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        approved_tmpl = tmpl_fixtures.create_template()
        pending_tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[pending_tmpl.to_dict()])
        UserFactory(info=user_info)
        category.info['templates'] = [approved_tmpl.to_dict()]
        self.project_repo.update_category(category)
        retrieved = [t.to_dict()
                     for t in self.project_tmpl_repo.get_all_pending()]
        expected = [pending_tmpl.to_dict()]
        assert_equal(retrieved, expected)

    @with_context
    def test_get_by_owner_returns_owners_templates(self):
        """Test get by owner returns owner's templates."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        owner = UserFactory(info=user_info)
        templates = self.project_tmpl_repo.get_by_owner_id(owner.id)
        retrieved = [t.to_dict() for t in templates]
        expected = [tmpl.to_dict()]
        assert_equal(retrieved, expected)

    @with_context
    def test_get_by_owner_prefers_user_templates(self):
        """Test get by owner prefers User over Category context."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        original_name = tmpl.name
        user_info = dict(templates=[tmpl.to_dict()])
        owner = UserFactory(info=user_info)
        tmpl.name = 'foo'
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        templates = self.project_tmpl_repo.get_by_owner_id(owner.id)
        retrieved = [t.to_dict() for t in templates]
        tmpl.name = original_name
        expected = [tmpl.to_dict()]
        assert_equal(retrieved, expected)

    @with_context
    def test_get_by_category_returns_categorys_templates(self):
        """Test get by category returns category's templates."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        templates = self.project_tmpl_repo.get_by_category_id(category.id)
        retrieved = [t.to_dict() for t in templates]
        expected = [tmpl.to_dict()]
        assert_equal(retrieved, expected)

    @with_context
    def test_update(self):
        """Test template is updated."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        name = 'New Name'
        tmpl.name = name

        not_updated_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_not_equal(not_updated_tmpl.name, name)

        self.project_tmpl_repo.update(tmpl)
        updated_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), updated_tmpl.to_dict())

    @with_context
    def test_update_pending(self):
        """Test pending template is updated."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)
        name = 'New Name'
        tmpl.name = name

        not_updated_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_not_equal(not_updated_tmpl.name, name)

        self.project_tmpl_repo.update_pending(tmpl)
        updated_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), updated_tmpl.to_dict())

    @with_context
    def test_save(self):
        """Test new templates are saved to the owner."""
        category = CategoryFactory()
        user = UserFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.owner_id = user.id

        not_pending_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_equal(not_pending_tmpl, None)

        self.project_tmpl_repo.save(tmpl)
        pending_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), pending_tmpl.to_dict())

        not_approved = self.project_tmpl_repo.get(tmpl.id)
        assert_equal(not_approved, None)

    @with_context
    def test_approved(self):
        """Test templates approved."""
        category = CategoryFactory()
        user = UserFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.owner_id = user.id
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)

        not_approved = self.project_tmpl_repo.get(tmpl.id)
        assert_equal(not_approved, None)

        self.project_tmpl_repo.approve(tmpl)
        approved_tmpl = self.project_tmpl_repo.get(tmpl.id)
        assert_dict_equal(tmpl.to_dict(), approved_tmpl.to_dict())

        not_pending_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_equal(not_pending_tmpl.pending, False)

    @with_context
    def test_delete_pending(self):
        """Test pending template is deleted."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user_info = dict(templates=[tmpl.to_dict()])
        UserFactory(info=user_info)

        not_deleted_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_dict_equal(not_deleted_tmpl.to_dict(), tmpl.to_dict())

        self.project_tmpl_repo.delete_pending(tmpl)
        deleted_tmpl = self.project_tmpl_repo.get_pending(tmpl.id)
        assert_equal(deleted_tmpl, None)

    @with_context
    def test_bad_objects_identified_templates(self):
        """Test non-templates raise WrongObjectErrors."""
        bad_object = dict()
        functions = [
            self.project_tmpl_repo.save,
            self.project_tmpl_repo.approve,
            self.project_tmpl_repo.update,
            self.project_tmpl_repo.update_pending
        ]
        for func in functions:
            assert_raises(WrongObjectError, func, bad_object)


