# -*- coding: utf8 -*-
"""Test Z39.50 analyst."""

import pandas
from nose.tools import *
from default import Test, with_context, db
from factories import TaskFactory, TaskRunFactory, CategoryFactory
from factories import ProjectFactory
from pybossa.repositories import ProjectRepository, ResultRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.analysis.z3950 import Z3950Analyst


class TestZ3950Analyst(Test):

    def setUp(self):
        super(TestZ3950Analyst, self).setUp()
        self.z3950_analyst = Z3950Analyst()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)

        self.data = {
            'user_id': [1],
            'control_number': ['123'],
            'reference': ['abc'],
            'foo': ['bar'],
            'comments': ['Some comment']
        }

    def create_task_with_context(self, n_answers, target, max_answers=None):
        """Create a category, project and tasks."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        tmpl.min_answers = n_answers
        tmpl.max_answers = max_answers or n_answers
        tmpl.rules = dict(case='title', whitespace='full_stop',
                          trim_punctuation=True)
        project_info = dict(template_id=tmpl.id)
        category.info['templates'] = [tmpl.to_dict()]
        self.project_repo.update_category(category)
        project = ProjectFactory.create(category=category, info=project_info)
        task_info = dict(target=target)
        return TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)

    def test_get_comments(self):
        """Test Z3950 comments are returned."""
        task_run_df = pandas.DataFrame(self.data)
        comments = self.z3950_analyst.get_comments(task_run_df)
        expected = [(self.data['user_id'][i], self.data['comments'][i])
                    for i in range(len(self.data['user_id']))]
        assert_equal(comments, expected)

    def test_get_tags(self):
        """Test Z3950 tags are returned."""
        task_run_df = pandas.DataFrame(self.data)
        tags = self.z3950_analyst.get_tags(task_run_df)
        assert_dict_equal(tags, {})

    def test_get_transcriptions_df(self):
        """Test Z3950 transcriptions are returned."""
        task_run_df = pandas.DataFrame(self.data)
        df = self.z3950_analyst.get_transcriptions_df(task_run_df)
        assert_dict_equal(df.to_dict(), {
            'control_number': dict(enumerate(self.data['control_number'])),
            'reference': dict(enumerate(self.data['reference']))
        })

    @with_context
    def test_analysis_with_empty_ansers(self):
        """Test Z3950 analysis with empty answers."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'control_number': '',
            'reference': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.z3950_analyst.analyse(result.id)
        assert_equal(result.info, {
            'annotations': []
        })

    @with_context
    def test_analysis_with_old_keys(self):
        """Test Z3950 analysis with old keys."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            'oclc': '',
            'shelfmark': '',
            'comments': ''
        })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.z3950_analyst.analyse(result.id)
        assert_equal(result.info, {
            'annotations': []
        })
