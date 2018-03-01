# -*- coding: utf8 -*-
"""Test background jobs."""

from mock import patch, MagicMock
from nose.tools import *
from default import Test, db, with_context, flask_app
from factories import ProjectFactory, TaskFactory, TaskRunFactory
from factories import CategoryFactory, UserFactory
from pybossa.repositories import ResultRepository, ProjectRepository
from pybossa.repositories import AnnouncementRepository

from pybossa_lc import jobs
from .fixtures import TemplateFixtures


class TestJobs(Test):

    def setUp(self):
        super(TestJobs, self).setUp()
        self.result_repo = ResultRepository(db)
        self.project_repo = ProjectRepository(db)
        self.announcement_repo = AnnouncementRepository(db)

    @with_context
    def test_missing_templates_identified(self):
        """Check that missing templates are identified."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        category.info = dict(templates=[tmpl.to_dict()])
        self.project_repo.update_category(category)

        ProjectFactory.create(info=dict(template_id=tmpl.id))
        empty_proj = ProjectFactory.create()
        jobs.check_for_invalid_templates()

        spa_server_name = self.flask_app.config.get('SPA_SERVER_NAME')
        endpoint = self.flask_app.config.get('PROJECT_TMPL_ENDPOINT')
        launch_url = spa_server_name + endpoint.format(empty_proj.short_name)
        announcements = self.announcement_repo.get_all_announcements()
        assert_equal(len(announcements), 1)
        assert_equal(announcements[0].title, 'Missing Template')
        assert_equal(announcements[0].body, empty_proj.name)
        assert_equal(announcements[0].published, True)
        assert_dict_equal(announcements[0].info, {
            'admin': True,
            'url': launch_url
        })

    @with_context
    @patch('pybossa_lc.jobs.get_analyst')
    def test_populate_empty_results(self, mock_get_analyst):
        """Check that empty IIIF Annotation results are analysed."""
        mock_analyst = MagicMock()
        mock_get_analyst.return_value = mock_analyst
        presenter = 'foo'
        category = CategoryFactory(info=dict(presenter=presenter))
        project = ProjectFactory.create(category=category)
        task = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task)
        jobs.populate_empty_results()
        mock_get_analyst.assert_called_once_with(presenter)
        mock_analyst.analyse_empty.assert_called_once_with(project.id)
