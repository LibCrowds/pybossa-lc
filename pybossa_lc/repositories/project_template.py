# -*- coding: utf8 -*-
"""Project template repository module."""

import itertools
from sqlalchemy.exc import IntegrityError
from pybossa.model.user import User
from pybossa.model.category import Category
from pybossa.exc import WrongObjectError, DBIntegrityError

from ..model.project_template import ProjectTemplate
from . import Repository


class ProjectTemplateRepository(Repository):

    def get(self, id):
        """Get an approved template from Category context."""
        filter_dict = {'templates': [{'id': id}]}
        category = self.db.session.query(Category).filter(
          Category.info.contains(filter_dict)
        ).first()
        if not category:
            return None

        templates = category.info.get('templates', [])
        tmpl_dict = [tmpl for tmpl in templates if tmpl['id'] == id][0]
        return self._convert_to_object(tmpl_dict)

    def get_pending(self, id):
        """Get a template from User context."""
        filter_dict = {'templates': [{'id': id}]}
        user = self.db.session.query(User).filter(
          User.info.contains(filter_dict)
        ).first()
        if not user:
            return None

        templates = user.info.get('templates', [])
        tmpl_dict = [tmpl for tmpl in templates if tmpl['id'] == id][0]
        return self._convert_to_object(tmpl_dict)

    def get_all(self):
        """Get all approved templates from Category context."""
        categories = self.db.session.query(Category).filter(
          Category.info.has_key('templates')
        ).all()

        tmpl_lists = [cat.info.get('templates', []) for cat in categories]
        tmpl_dicts = itertools.chain(*tmpl_lists)
        return map(self._convert_to_object, tmpl_dicts)

    def get_all_pending(self):
        """Get all pending templates from User context."""
        users = self.db.session.query(User).filter(
          User.info.has_key('templates')
        ).all()

        tmpl_lists = [user.info.get('templates', []) for user in users]
        tmpl_dicts = itertools.chain(*tmpl_lists)
        return map(self._convert_to_object, tmpl_dicts)

    def get_by_owner_id(self, owner_id):
        """Get all of a user's templates."""
        filter_dict = {'templates': [{'owner_id': owner_id}]}
        users = self.db.session.query(User).filter(
          User.info.contains(filter_dict)
        ).all()
        categories = self.db.session.query(Category).filter(
          Category.info.contains(filter_dict)
        ).all()

        user_templates = list(itertools.chain(*[u.info.get('templates', [])
                                                for u in users]))
        category_templates = list(itertools.chain(*[c.info.get('templates', [])
                                                    for c in categories]))
        user_tmpl_ids = [tmpl['id'] for tmpl in user_templates]
        user_templates += [tmpl for tmpl in category_templates
                           if tmpl['id'] not in user_tmpl_ids]
        return map(self._convert_to_object, user_templates)

    def get_by_category_id(self, category_id):
        """Get all of a category's templates."""
        category = self.db.session.query(Category).get(category_id)
        tmpl_dicts = category.info.get('templates', [])
        return map(self._convert_to_object, tmpl_dicts)

    def save(self, tmpl):
        """Save a template to the User."""
        self._validate_can_be('saved', tmpl)
        user = self.db.session.query(User).get(tmpl.owner_id)
        tmpl_dict = tmpl.to_dict()
        templates = user.info.get('templates', [])
        already_exists = [t for t in templates if t['id'] == tmpl.id]
        if already_exists:  # pragma: no cover
            raise ValueError('Template ID already exists')

        templates.append(tmpl_dict)
        user.info['templates'] = templates
        try:
            self.db.session.merge(user)
            self.db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def approve(self, tmpl):
        """Remove a template from user context and add it to the category."""
        self._validate_can_be('saved', tmpl)
        tmpl.pending = False
        user = self.db.session.query(User).filter(
          User.info.contains({'templates': [{'id': tmpl.id}]})
        ).first()
        category = self.db.session.query(Category).get(tmpl.category_id)
        if not category:  # pragma: no cover
            raise ValueError('Template category does not exist')
        elif not user:  # pragma: no cover
            raise ValueError('Template owner does not exist')

        self._update_container_templates(tmpl, user)
        self._update_container_templates(tmpl, category, ignore_error=True)
        try:
            self.db.session.merge(user)
            self.db.session.merge(category)
            self.db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, tmpl, approved=False):
        """Update a template."""
        self._validate_can_be('updated', tmpl)
        category = self.db.session.query(Category).get(tmpl.category_id)
        if not category:  # pragma: no cover
            raise ValueError('Template category does not exist')

        self._update_container_templates(tmpl, category)
        try:
            self.db.session.merge(category)
            self.db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update_pending(self, tmpl):
        """Update a pending template."""
        self._validate_can_be('updated', tmpl)
        user = self.db.session.query(User).get(tmpl.owner_id)
        if not user:  # pragma: no cover
            raise ValueError('Template owner does not exist')

        self._update_container_templates(tmpl, user)
        try:
            self.db.session.merge(user)
            self.db.session.commit()
        except IntegrityError as e:  # pragma: no cover
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def _validate_can_be(self, action, element):
        """Return related Category if approved else related User."""
        name = element.__class__.__name__
        msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
        if not isinstance(element, ProjectTemplate):
            raise WrongObjectError(msg)

    def _convert_to_object(self, template_dict):
        """Convert a template dict to an object."""
        tmpl = ProjectTemplate(**template_dict)
        tmpl.id = template_dict['id']
        tmpl.created = template_dict['created']
        return tmpl

    def _update_container_templates(self, tmpl, container, ignore_error=False):
        """Update a template in a User or Category."""
        templates = container.info.get('templates', [])
        try:
            idx = [i for i, t in enumerate(templates) if t['id'] == tmpl.id][0]
            templates[idx] = tmpl.to_dict()
        except IndexError:  # pragma: no cover
            if not ignore_error:
                raise ValueError('Template does not exist')
            templates.append(tmpl.to_dict())
        container.info['templates'] = templates
