# -*- coding: utf8 -*-
"""Test background jobs."""

from mock import patch, MagicMock, call
from nose.tools import *
from default import Test, db, with_context, flask_app
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory, UserFactory
from pybossa.repositories import ResultRepository, ProjectRepository
from pybossa.repositories import AnnouncementRepository

from pybossa_lc import jobs
from .fixtures.template import TemplateFixtures


class TestJobs(Test):

    def setUp(self):
        super(TestJobs, self).setUp()
        self.result_repo = ResultRepository(db)
        self.project_repo = ProjectRepository(db)
        self.announcement_repo = AnnouncementRepository(db)

    @with_context
    @patch('pybossa_lc.jobs.send_mail')
    def test_invalid_templates_identified(self, mock_send_mail):
        """Check that invalid templates are identified."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create()
        category.info = dict(templates=[tmpl.to_dict()], published=True)
        self.project_repo.update_category(category)

        ProjectFactory.create(category=category,
                              info=dict(template_id=tmpl.id))
        invalid_proj = ProjectFactory.create(category=category,
                                             info=dict(template_id='foo'))
        empty_proj = ProjectFactory.create(category=category)
        jobs.check_for_invalid_templates()

        url_base = flask_app.config.get('SPA_SERVER_NAME') + '/api/project'

        # Check email sent about invalid template
        subject = "PROJECT {0}: Invalid Template".format(invalid_proj.id)
        body = "Please review the following project:"
        body += "\n\n"
        body += invalid_proj.name
        body += "\n\n"
        body += "{0}/{1}".format(url_base, invalid_proj.id)
        mail_dict1 = dict(recipients=flask_app.config.get('ADMINS'),
                          subject=subject, body=body)

        # Check email sent about missing template
        subject = "PROJECT {0}: Invalid Template".format(empty_proj.id)
        body = "Please review the following project:"
        body += "\n\n"
        body += empty_proj.name
        body += "\n\n"
        body += "{0}/{1}".format(url_base, empty_proj.id)
        mail_dict2 = dict(recipients=flask_app.config.get('ADMINS'),
                          subject=subject, body=body)

        assert_equal(mock_send_mail.call_args_list, [
            call(mail_dict1),
            call(mail_dict2)
        ])

    @with_context
    @patch('pybossa_lc.jobs.send_mail')
    def test_invalid_volumes_identified(self, mock_send_mail):
        """Check that invalid volumes are identified."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        vol = dict(id='foo', name='bar')
        category.info = dict(volumes=[vol], published=True)
        self.project_repo.update_category(category)

        ProjectFactory.create(category=category,
                              info=dict(volume_id=vol['id']))
        invalid_proj = ProjectFactory.create(category=category,
                                             info=dict(volume_id='baz'))
        empty_proj = ProjectFactory.create(category=category)
        jobs.check_for_invalid_volumes()

        url_base = flask_app.config.get('SPA_SERVER_NAME') + '/api/project'

        # Check email sent about invalid template
        subject = "PROJECT {0}: Invalid Volume".format(invalid_proj.id)
        body = "Please review the following project:"
        body += "\n\n"
        body += invalid_proj.name
        body += "\n\n"
        body += "{0}/{1}".format(url_base, invalid_proj.id)
        mail_dict1 = dict(recipients=flask_app.config.get('ADMINS'),
                          subject=subject, body=body)

        # Check email sent about missing template
        subject = "PROJECT {0}: Invalid Volume".format(empty_proj.id)
        body = "Please review the following project:"
        body += "\n\n"
        body += empty_proj.name
        body += "\n\n"
        body += "{0}/{1}".format(url_base, empty_proj.id)
        mail_dict2 = dict(recipients=flask_app.config.get('ADMINS'),
                          subject=subject, body=body)

        assert_equal(mock_send_mail.call_args_list, [
            call(mail_dict1),
            call(mail_dict2)
        ])
