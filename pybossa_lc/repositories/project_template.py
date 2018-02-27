# -*- coding: utf8 -*-
"""Project template repository module."""

from sqlalchemy.exc import IntegrityError
from pybossa.model.user import User
from pybossa.model.category import Category
from pybossa.exc import WrongObjectError, DBIntegrityError

from ..model.project_template import ProjectTemplate
from . import Repository


class ProjectTemplateRepository(Repository):

    def get(self, id):
        """Get a template object from User info."""
        filter_dict = {'templates': [{'id': id}]}
        user = self.db.session.query(User).filter(
          User.info.contains(filter_dict)
        ).first()
        if not user:
            return None

        # Return as a ProjectTemplate object
        templates = user.info.get('templates', [])
        tmpl_dict = [tmpl for tmpl in templates if tmpl['id'] == id][0]
        tmpl = ProjectTemplate(**tmpl_dict)
        tmpl.id = tmpl_dict['id']
        tmpl.created = tmpl_dict['created']
        return tmpl

    def get_all(self):
        """Get all User templates."""
        users = self.db.session.query(User).filter(
          User.info.has_key('templates')
        ).all()

        # Return as a ProjectTemplate object
        templates = []
        for user in users:
            user_templates = user.info.get('templates', [])
            for tmpl_dict in user_templates:
                tmpl = ProjectTemplate(**tmpl_dict)
                tmpl.id = tmpl_dict['id']
                tmpl.created = tmpl_dict['created']
                templates.append(tmpl)
        return templates

    def get_by_owner_id(self, owner_id):
        """Get all of a specific user's templates."""
        user = self.db.session.query(User).first()

        # Return as a ProjectTemplate object
        templates = []
        user_templates = user.info.get('templates', [])
        for tmpl_dict in user_templates:
            tmpl = ProjectTemplate(**tmpl_dict)
            tmpl.id = tmpl_dict['id']
            tmpl.created = tmpl_dict['created']
            templates.append(tmpl)
        return templates

    def get_approved(self, id):
        """Get an approved template object from Category info."""
        filter_dict = {'templates': [{'id': id, 'pending': False}]}
        category = self.db.session.query(Category).filter(
          Category.info.contains(filter_dict)
        ).first()
        if not category:
            return None

        # Return as a ProjectTemplate object
        templates = category.info.get('templates', [])
        tmpl_dict = [tmpl for tmpl in templates if tmpl['id'] == id][0]
        tmpl = ProjectTemplate(**tmpl_dict)
        tmpl.id = tmpl_dict['id']
        tmpl.created = tmpl_dict['created']
        return tmpl

    def save(self, tmpl, approved=False):
        """Save a template."""
        container = self._get_valid_container('saved', tmpl, approved)
        tmpl.pending = not approved
        tmpl_dict = tmpl.to_dict()
        templates = container.info.get('templates', [])
        already_exists = [t for t in templates if t['id'] == tmpl.id]
        if already_exists:
            raise ValueError('Template ID already exists')

        templates.append(tmpl_dict)
        container.info['templates'] = templates
        try:
            self.db.session.merge(container)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    def update(self, tmpl, approved=False):
        container = self._get_valid_container('updated', tmpl, approved)
        tmpl.pending = not approved
        templates = container.info.get('templates', [])
        try:
            idx = [i for i, t in enumerate(templates) if t['id'] == tmpl.id][0]
        except IndexError:
            raise ValueError('Template does not exist')

        templates[idx] = tmpl.to_dict()
        container.info['templates'] = templates
        try:
            self.db.session.merge(container)
            self.db.session.commit()
        except IntegrityError as e:
            self.db.session.rollback()
            raise DBIntegrityError(e)

    # def delete(self, hm):
    #     self._validate_can_be('deleted', hm)
    #     blog = self.db.session.query(HelpingMaterial).filter(HelpingMaterial.id==hm.id).first()
    #     self.db.session.delete(blog)
    #     self.db.session.commit()

    def _get_valid_container(self, action, element, approved=False):
        """Return related Category if approved else related User."""
        name = element.__class__.__name__
        msg = '%s cannot be %s by %s' % (name, action, self.__class__.__name__)
        if not isinstance(element, ProjectTemplate):
            raise WrongObjectError(msg)

        if approved:
            return self.db.session.query(Category).get(element.category_id)
        else:
            return self.db.session.query(User).get(element.owner_id)

