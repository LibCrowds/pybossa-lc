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
        field = dict(label='Title', type='input', inputType='text',
                     placeholder='', model='title')
        self.iiif_select_tmpl = dict(
            id=12345, name='Mark Up', tag='title', mode='select',
            objective='Mark up the title', guidance='Do it now',
            tutorial='Do stuff', description='This project is amazing'
        )
        self.iiif_transcribe_tmpl = dict(
            id=12345, name='Transcribe', tag='title', mode='transcribe',
            objective='Transcribe the title', guidance='Do it now',
            tutorial='Do stuff', fields_schema=[field],
            description='This project is amazing'
        )
        z3950_db = self.flask_app.config['Z3950_DATABASES'].keys()[0]
        self.z3950_tmpl = dict(
            id=12345, name='Search', description='This project is amazing',
            tutorial='Do stuff', database=z3950_db, institutions=['OCLC']
        )

    @with_context
    def test_add_template_auth(self):
        """Test authorisation for the add template endpoint."""
        category = CategoryFactory.create()
        endpoint = '/libcrowds/categories/{}/templates'.format(category.id)

        # Test anon user unauthorised
        res = self.app_get_json(endpoint)
        assert_equal(res.status_code, 401)

        # Test non-admin forbidden
        self.register()
        self.signout()
        self.register(fullname="jane", name="jane", email="jane@jane.com")
        res = self.app_get_json(endpoint)
        assert_equal(res.status_code, 403)

        # Test admin user authorised
        self.register()
        self.signin()
        res = self.app_get_json(endpoint, follow_redirects=True)
        assert_equal(res.status_code, 200)

        # Test redirects without a task presenter
        assert_equal(json.loads(res.data)['next'], "/admin/categories")

    @with_context
    def test_add_iiif_transcribe_template(self):
        """Test a IIIF transcribe template is added."""
        self.register()
        self.signin()
        info = dict(presenter='iiif-annotation')
        category = CategoryFactory.create(info=info)
        endpoint = '/libcrowds/categories/{}/templates'.format(category.id)
        res = self.app_post_json(endpoint, data=self.iiif_transcribe_tmpl)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert_equal(json.loads(res.data)['flash'], 'Project template created')
        assert_equal(len(templates), 1)
        del self.iiif_transcribe_tmpl['id']
        del templates[0]['id']
        assert_dict_equal(templates[0], self.iiif_transcribe_tmpl)

    @with_context
    def test_add_iiif_select_template(self):
        """Test a IIIF select template is added."""
        self.register()
        self.signin()
        info = dict(presenter='iiif-annotation')
        category = CategoryFactory.create(info=info)
        endpoint = '/libcrowds/categories/{}/templates'.format(category.id)
        res = self.app_post_json(endpoint, data=self.iiif_select_tmpl)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert_equal(json.loads(res.data)['flash'], 'Project template created')
        assert_equal(len(templates), 1)
        del self.iiif_select_tmpl['id']
        del templates[0]['id']
        assert_dict_equal(templates[0], self.iiif_select_tmpl)

    @with_context
    def test_add_z3950_template(self):
        """Test a Z39.50 template is added."""
        self.register()
        self.signin()
        info = dict(presenter='z3950')
        category = CategoryFactory.create(info=info)
        endpoint = '/libcrowds/categories/{}/templates'.format(category.id)
        res = self.app_post_json(endpoint, data=self.z3950_tmpl)
        updated_category = self.project_repo.get_category(category.id)
        templates = updated_category.info.get('templates')
        assert_equal(json.loads(res.data)['flash'], 'Project template created')
        assert_equal(len(templates), 1)
        del self.z3950_tmpl['id']
        del templates[0]['id']
        assert_dict_equal(templates[0], self.z3950_tmpl)

    # @with_context
    # def test_update_template(self):
    #     """Test the update template endpoint."""
    #     info = dict(templates=[self.iiif_transcribe_tmpl])
    #     category = CategoryFactory.create(info=info)
    #     url_tmpl = '/libcrowds/categories/{}/templates/{}'
    #     endpoint = url_tmpl.format(category.id,
    #                                self.iiif_transcribe_tmpl['id'])

    #     # Test anon user unauthorised
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 401)

    #     # Test non-admin forbidden
    #     self.register()
    #     self.signout()
    #     self.register(fullname="jane", name="jane", email="jane@jane.com")
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 403)

    #     # Test admin user authorised
    #     self.signin()
    #     res = self.app_get_json(endpoint)
    #     assert_equal(res.status_code, 200)

    #     # Test redirects without a task presenter
    #     assert_equal(json.loads(res.data)['next'], "/admin/categories")
    #     category.info['presenter'] = 'iiif-annotation'
    #     self.project_repo.update_category(category)

    #     # Test form is populated
    #     form = json.loads(res.data)['form']
    #     form_fields = {k: v for k, v in form.items()
    #                    if k not in ['csrf', 'errors']}
    #     assert_dict_equal(form_fields, self.iiif_transcribe_tmpl)

    #     # Test that a template is updated
    #     self.iiif_transcribe_tmpl['name'] = 'A new name'
    #     res = self.app_post_json(endpoint, data=self.iiif_transcribe_tmpl)
    #     updated_category = self.project_repo.get_category(category.id)
    #     templates = updated_category.info.get('templates')
    #     assert_equal(json.loads(res.data)['flash'], 'Project template updated')
    #     assert_equal(len(templates), 1)
    #     assert_dict_equal(templates[0], self.iiif_transcribe_tmpl)

    # @with_context
    # def test_delete_template(self):
    #     """Test the delete template endpoint."""
    #     info = dict(templates=[self.iiif_transcribe_tmpl])
    #     category = CategoryFactory.create(info=info)
    #     url_tmpl = '/libcrowds/categories/{}/templates/{}/delete'
    #     endpoint = url_tmpl.format(category.id,
    #                                self.iiif_transcribe_tmpl['id'])

    #     # Test anon user unauthorised
    #     res = self.app_post_json(endpoint)
    #     assert_equal(res.status_code, 401)

    #     # Test non-admin forbidden
    #     self.register()
    #     self.signout()
    #     self.register(fullname="jane", name="jane", email="jane@jane.com")
    #     res = self.app_post_json(endpoint)
    #     assert_equal(res.status_code, 403)

    #     # Test that a template is deleted for admin users
    #     self.register()
    #     self.signin()
    #     res = self.app_post_json(endpoint)
    #     updated_category = self.project_repo.get_category(category.id)
    #     assert_equal(json.loads(res.data)['flash'], 'Project template deleted')
    #     assert not updated_category.info.get('templates')
