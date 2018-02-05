# -*- coding: utf8 -*-
"""Test background jobs."""

from mock import patch
from nose.tools import *
from default import Test, db, with_context, flask_app
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory, UserFactory
from pybossa.repositories import ResultRepository, UserRepository
from pybossa.repositories import AnnouncementRepository

from pybossa_lc import jobs
from .fixtures import TemplateFixtures

class TestJobs(Test):

    def setUp(self):
        super(TestJobs, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)
        self.announcement_repo = AnnouncementRepository(db)

    @with_context
    def test_empty_templates_identified(self):
        """Check that empty templates are identified."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        user = UserFactory.create(info=dict(templates=[tmpl]))
        self.user_repo.update(user)

        info = dict(template_id=tmpl['id'])
        project1 = ProjectFactory.create(info=info)
        project2 = ProjectFactory.create()
        jobs.check_for_missing_templates()

        spa_server_name = self.flask_app.config.get('SPA_SERVER_NAME')
        endpoint = self.flask_app.config.get('PROJECT_TMPL_ENDPOINT')
        launch_url = spa_server_name + endpoint.format(project2.short_name)
        announcements = self.announcement_repo.get_all_announcements()
        assert_equal(len(announcements), 1)
        assert_equal(announcements[0].title, 'Missing Template')
        assert_equal(announcements[0].body, project2.name)
        assert_equal(announcements[0].published, True)
        assert_dict_equal(announcements[0].info, {
            'admin': True,
            'url': launch_url
        })

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.analyse_empty')
    def test_populate_empty_iiif_annotation_results(self, mock_analyse):
        """Check that empty IIIF Annotation results are analysed."""
        category = CategoryFactory(info=dict(presenter='iiif-annotation'))
        project = ProjectFactory.create(category=category)
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        jobs.populate_empty_results()
        mock_analyse.assert_called_once_with(project.id)

    @with_context
    @patch('pybossa_lc.analysis.z3950.analyse_empty')
    def test_populate_empty_z3950_results(self, mock_analyse):
        """Check that empty Z3950 results are analysed."""
        category = CategoryFactory(info=dict(presenter='z3950'))
        project = ProjectFactory.create(category=category)
        task = TaskFactory.create(project=project, n_answers=1)
        tr_info = dict(comments='', reference='', control_number='')
        TaskRunFactory.create(task=task, info=tr_info)
        jobs.populate_empty_results()
        mock_analyse.assert_called_once_with(project.id)
