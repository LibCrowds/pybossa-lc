# -*- coding: utf8 -*-
"""Test category API."""

import json
from mock import patch, MagicMock
from nose.tools import *
from helper import web
from default import with_context, db
from factories import CategoryFactory
from pybossa.repositories import ProjectRepository
from pybossa.jobs import import_tasks
from pybossa.core import task_repo

from pybossa_lc.forms import *


class TestCategoryApi(web.Helper):

    def setUp(self):
        super(TestCategoryApi, self).setUp()
        self.project_repo = ProjectRepository(db)

    @with_context
    def test_add_template(self):
        """Test the add template endpoint."""
        category = CategoryFactory.create()
        endpoint = '/libcrowds/categories/{}/templates'.format(category.id)

        # Test anon user unauthorised
        res = self.app_get_json(endpoint)
        assert res.status_code == 401, res

        # Test non-admin forbidden
        self.register()
        self.signout()
        self.register(fullname="jane", name="jane", email="jane@jane.com")
        res = self.app_get_json(endpoint)
        assert res.status_code == 403, res

        # Test admin user authorised
        self.register()
        self.signin()
        res = self.app_get_json(endpoint)
        assert res.status_code == 200

        # Test that a valid template is added
        payload = dict(name='Transcribe', tag='title',
                       objective='Transcribe the title', guidance='Do it now',
                       description='This project is amazing',
                       mode='select')
        res = self.app_post_json(endpoint, data=payload)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert len(templates) == 1
        assert json.loads(res.data)['flash'] == 'Project template created'
        for key, value in payload.items():
            assert templates[0][key] == value

        # Test that an invalid template is not added
        payload = dict(foo='bar')
        res = self.app_post_json(endpoint, data=payload)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert json.loads(res.data)['flash'] == 'Please correct the errors'
        assert len(templates) == 1

    @with_context
    def test_update_template(self):
        """Test the update template endpoint."""
        tmpl = dict(id=12345, name='Transcribe', tag='title',
                    objective='Transcribe the title', guidance='Do it now',
                    description='This project is amazing', mode='select',
                    tutorial='Do stuff')
        info = dict(templates=[tmpl])
        category = CategoryFactory.create(info=info)
        endpoint = '/libcrowds/categories/{}/templates/{}'.format(category.id,
                                                                  tmpl['id'])

        # Test anon user unauthorised
        res = self.app_get_json(endpoint)
        assert res.status_code == 401, res

        # Test non-admin forbidden
        self.register()
        self.signout()
        self.register(fullname="jane", name="jane", email="jane@jane.com")
        res = self.app_get_json(endpoint)
        assert res.status_code == 403, res

        # Test admin user authorised
        self.signin()
        res = self.app_get_json(endpoint)
        assert res.status_code == 200

        # Test form is populated
        form = json.loads(res.data)['form']
        fields = {k: v for k, v in form.items()
                  if k not in ['csrf', 'errors']}
        assert_dict_equal(fields, tmpl)

        # Test that a template is updated
        tmpl['name'] = 'A new name'
        res = self.app_post_json(endpoint, data=tmpl)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert json.loads(res.data)['flash'] == 'Project template updated'
        assert len(templates) == 1
        for key, value in tmpl.items():
            assert templates[0][key] == value

    @with_context
    def test_delete_template(self):
        """Test the delete template endpoint."""
        tmpl = dict(id=12345, name='Transcribe', tag='title',
                    objective='Transcribe the title', guidance='Do it now',
                    description='This project is amazing', mode='select')
        info = dict(templates=[tmpl])
        category = CategoryFactory.create(info=info)
        endpoint_base = '/libcrowds/categories/{}/templates/{}/delete'
        endpoint = endpoint_base.format(category.id, tmpl['id'])

        # Test anon user unauthorised
        res = self.app_post_json(endpoint)
        assert res.status_code == 401, res

        # Test non-admin forbidden
        self.register()
        self.signout()
        self.register(fullname="jane", name="jane", email="jane@jane.com")
        res = self.app_post_json(endpoint)
        assert res.status_code == 403, res

        # Test that a template is delete for admin users
        self.register()
        self.signin()
        res = self.app_post_json(endpoint)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert json.loads(res.data)['flash'] == 'Project template deleted'
        assert not templates
