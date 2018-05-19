# -*- coding: utf8 -*-
"""Test Base analyst."""

import json
import numpy
import pandas
from mock import patch, call, MagicMock
from factories import TaskFactory, TaskRunFactory, ProjectFactory, UserFactory
from factories import CategoryFactory
from default import db, Test, with_context, flask_app
from nose.tools import *
from pybossa.core import result_repo, task_repo
from pybossa.repositories import ResultRepository, TaskRepository
from pybossa.repositories import ProjectRepository

from ..fixtures.context import ContextFixtures
from ..fixtures.template import TemplateFixtures
from pybossa_lc.analysis.base import BaseAnalyst
from pybossa_lc.analysis import AnalysisException


class TestBaseAnalyst(Test):

    def setUp(self):
        super(TestBaseAnalyst, self).setUp()
        BaseAnalyst.__abstractmethods__ = frozenset()
        self.ctx = ContextFixtures()
        self.base_analyst = BaseAnalyst()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)
        assert_dict_equal.__self__.maxDiff = None
        assert_equal.__self__.maxDiff = None

    @with_context
    @patch("pybossa_lc.analysis.base.BaseAnalyst.analyse")
    def test_analyse_all(self, mock_analyse):
        """Test that all results are analysed."""
        project = ProjectFactory()
        tasks = TaskFactory.create_batch(2, project=project, n_answers=1)
        for task in tasks:
            TaskRunFactory.create(task=task)
        result = self.result_repo.get_by(task_id=tasks[0].id)
        result.info = dict(annotations=[{}])
        self.result_repo.update(result)
        self.base_analyst.analyse_all(project.id)
        expected = [call(t.id) for t in tasks]
        assert_equal(mock_analyse.call_args_list, expected)

    @with_context
    @patch("pybossa_lc.analysis.base.BaseAnalyst.analyse")
    def test_analyse_empty(self, mock_analyse):
        """Test that all results are analysed."""
        project = ProjectFactory()
        tasks = TaskFactory.create_batch(2, project=project, n_answers=1)
        for task in tasks:
            TaskRunFactory.create(task=task)
        result = self.result_repo.get_by(task_id=tasks[0].id)
        result.info = dict(annotations=[{}])
        self.result_repo.update(result)
        all_results = self.result_repo.filter_by(project_id=project.id)
        self.base_analyst.analyse_empty(project.id)
        expected = [call(r.task_id) for r in all_results if not r.info]
        assert_equal(mock_analyse.call_args_list, expected)

    @with_context
    def test_key_dropped(self):
        """Test the correct keys are dropped."""
        data = [{
            'foo': None,
            'bar': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        excluded = ['foo']
        df = self.base_analyst.drop_keys(df, excluded)
        assert_not_in('foo', df.keys())
        assert_in('bar', df.keys())

    @with_context
    def test_empty_rows_dropped(self):
        """Test empty rows are dropped."""
        data = [{
            'foo': 'bar'
        }, {
            'foo': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = self.base_analyst.drop_empty_rows(df)
        assert_equals(df['foo'].tolist(), ['bar'])

    @with_context
    def test_partial_rows_not_dropped(self):
        """Test partial rows are not dropped."""
        data = [{
            'foo': 'bar',
            'baz': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = self.base_analyst.drop_empty_rows(df)
        expected = {'foo': {0: 'bar'}, 'baz': {0: None}}
        assert_dict_equal(df.to_dict(), expected)

    @with_context
    def test_match_fails_when_percentage_not_met(self):
        """Test False is returned when min answers not met."""
        data = [{
            'foo': 'bar',
            'baz': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        min_answers = 2
        has_matches = self.base_analyst.has_n_matches(min_answers, df)
        assert_equal(has_matches, False)

    @with_context
    def test_match_fails_when_nan_cols(self):
        """Test False is returned when NaN columns only."""
        data = [{
            'foo': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = df.replace('', numpy.nan)
        min_answers = 2
        has_matches = self.base_analyst.has_n_matches(min_answers, df)
        assert_equal(has_matches, False)

    @with_context
    def test_match_succeeds_when_percentage_met(self):
        """Test True returned when match percentage met."""
        data = [{
            'foo': 'bar'
        }, {
            'foo': 'bar'
        }]
        df = pandas.DataFrame(data, range(len(data)))
        min_answers = 2
        has_matches = self.base_analyst.has_n_matches(min_answers, df)
        assert_equal(has_matches, True)

    @with_context
    def test_get_dataframe_with_dict(self):
        """Test the task run dataframe with a dict as the info."""
        info = {'foo': 'bar'}
        n_task_runs = 2
        task = TaskFactory()
        taskruns = TaskRunFactory.create_batch(n_task_runs, task=task,
                                               info=info)
        df = self.base_analyst.get_task_run_df(task, taskruns)
        assert_equal(df['foo'].tolist(), [info['foo']] * n_task_runs)
        assert_equal(df['info'].tolist(), [info] * n_task_runs)

    @with_context
    def test_get_dataframe_with_list(self):
        """Test the task run dataframe with a list as the info."""
        info = [{'foo': 'bar'}, {'baz': 'qux'}]
        n_task_runs = 2
        task = TaskFactory()
        taskruns = TaskRunFactory.create_batch(n_task_runs, task=task,
                                               info=info)
        df = self.base_analyst.get_task_run_df(task, taskruns)
        assert_equal(df['info'].tolist(), [info] * n_task_runs)

    @with_context
    def test_protected_keys_prefixed_when_exploded(self):
        """Test that protected info keys are prefixed."""
        info = {'foo': 'bar', 'info': 'baz'}
        task = TaskFactory()
        taskrun = TaskRunFactory.create(task=task, info=info)
        df = self.base_analyst.get_task_run_df(task, [taskrun])
        assert_equal(df['_info'].tolist(), [info['info']])

    @with_context
    def test_user_ids_in_task_run_dataframe(self):
        """Test that user IDs are included in the task run dataframe."""
        task = TaskFactory()
        taskruns = TaskRunFactory.create_batch(2, task=task)
        df = self.base_analyst.get_task_run_df(task, taskruns)
        assert_equal(df['user_id'].tolist(), [tr.user_id for tr in taskruns])

    def test_titlecase_normalisation(self):
        """Test titlecase normalisation."""
        rules = dict(case='title')
        norm = self.base_analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'Some Words')

    def test_lowercase_normalisation(self):
        """Test lowercase normalisation."""
        rules = dict(case='lower')
        norm = self.base_analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'some words')

    def test_uppercase_normalisation(self):
        """Test uppercase normalisation."""
        rules = dict(case='upper')
        norm = self.base_analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'SOME WORDS')

    def test_whitespace_normalisation(self):
        """Test whitespace normalisation."""
        rules = dict(whitespace='normalise')
        norm = self.base_analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two Words')

    def test_whitespace_replace_underscore(self):
        """Test replacing whitespace with underscore normalisation."""
        rules = dict(whitespace='underscore')
        norm = self.base_analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two_Words')

    def test_whitespace_replace_full_stop(self):
        """Test replacing whitespace with full stop normalisation."""
        rules = dict(whitespace='full_stop')
        norm = self.base_analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two.Words')

    def test_trim_punctuation_normalisation(self):
        """Test trim punctuation normalisation."""
        rules = dict(trim_punctuation=True)
        norm = self.base_analyst.normalise_transcription(':Oh, a word.', rules)
        assert_equal(norm, 'Oh, a word')

    def test_date_not_normalised_if_rule_inactive(self):
        """Test date conversion not applied of rule not activate."""
        norm = self.base_analyst.normalise_transcription('foo', {})
        assert_equal(norm, 'foo')

    def test_date_conversion_with_slash(self):
        """Test date conversion with slash seperators."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19/11/1984', rules)
        assert_equal(norm, '1984-11-19')

    def test_date_conversion_with_hyphen(self):
        """Test date conversion with hyphen seperator."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19-11-1984', rules)
        assert_equal(norm, '1984-11-19')

    def test_date_conversion_with_no_seperator(self):
        """Test date conversion with no seperator."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19111984', rules)
        assert_equal(norm, '')

    def test_date_conversion_with_no_year_and_year_last(self):
        """Test date conversion with no year and year last."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19/11', rules)
        assert_equal(norm, '-11-19')

    def test_date_conversion_with_no_year_and_year_first(self):
        """Test date conversion with no year and year first."""
        rules = dict(date_format=True, yearfirst=True)
        norm = self.base_analyst.normalise_transcription('11/19', rules)
        assert_equal(norm, '-11-19')

    def test_date_conversion_with_invalid_string(self):
        """Test date conversion with invalid string."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('No date', rules)
        assert_equal(norm, '')

    def test_date_conversion_with_zero(self):
        """Test date conversion with zero."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('0', rules)
        assert_equal(norm, '')

    def test_date_conversion_with_non_zero_integer(self):
        """Test date conversion with non-zero integer."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('1', rules)
        assert_equal(norm, '')

    def test_date_conversion_with_trailing_punctuation(self):
        """Test date conversion with trailing punctuation."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19/11/', rules)
        assert_equal(norm, '-11-19')

    def test_date_conversion_with_trailing_whitespace(self):
        """Test date conversion with trailing whitespace."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.base_analyst.normalise_transcription('19/11/1984 ', rules)
        assert_equal(norm, '1984-11-19')

    @with_context
    def test_n_answers_increased_when_task_complete(self):
        """Test n answers required for a task is updated."""
        n_original_answers = 1
        task = TaskFactory.create(n_answers=n_original_answers)
        TaskRunFactory.create(task=task)
        self.base_analyst.update_n_answers_required(task, False)
        assert_equal(task.n_answers, n_original_answers + 1)
        assert_equal(task.state, 'ongoing')

    @with_context
    def test_n_answers_not_increased_when_still_task_runs(self):
        """Test n answers not updated when task runs still required."""
        n_original_answers = 2
        task = TaskFactory.create(n_answers=n_original_answers)
        TaskRunFactory.create(task=task)
        self.base_analyst.update_n_answers_required(task, False)
        assert_equal(task.n_answers, n_original_answers)
        assert_equal(task.state, 'ongoing')

    @with_context
    def test_n_answers_not_increased_when_max_answers_reached(self):
        """Test n answers not updated when max answers reached."""
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers)
        TaskRunFactory.create_batch(n_answers, task=task)
        self.base_analyst.update_n_answers_required(task, False,
                                                    max_answers=n_answers)
        assert_equal(task.n_answers, n_answers)
        assert_equal(task.state, 'completed')

    @with_context
    def test_n_answers_reduced_when_task_complete(self):
        """Test n answers reduced to number of task runs when task complete."""
        n_answers = 3
        task = TaskFactory.create(n_answers=n_answers)
        TaskRunFactory.create_batch(n_answers - 1, task=task)
        self.base_analyst.update_n_answers_required(task, True,
                                                    max_answers=n_answers)
        assert_equal(task.n_answers, n_answers - 1)
        assert_equal(task.state, 'completed')

    def test_overlap_ratio_is_1_with_equal_rects(self):
        """Test for an overlap ratio of 1."""
        rect = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        overlap = self.base_analyst.get_overlap_ratio(rect, rect)
        assert_equal(overlap, 1)

    def test_overlap_ratio_is_0_with_adjacent_rects(self):
        """Test for an overlap ratio of 0."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 100, 'y': 201, 'w': 100, 'h': 100}
        overlap = self.base_analyst.get_overlap_ratio(r1, r2)
        assert_equal(overlap, 0)

    def test_overlap_ratio_with_partially_overlapping_rects(self):
        """Test for an overlap ratio of 0.33."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 150, 'y': 100, 'w': 100, 'h': 100}
        overlap = self.base_analyst.get_overlap_ratio(r1, r2)
        assert_equal('{:.2f}'.format(overlap), '0.33')

    def test_overlap_ratio_where_union_is_zero(self):
        """Test for an overlap ratio where the union is zero."""
        r1 = {'x': 0, 'y': 0, 'w': 100, 'h': 100}
        r2 = {'x': 101, 'y': 0, 'w': 100, 'h': 100}
        overlap = self.base_analyst.get_overlap_ratio(r1, r2)
        assert_equal(overlap, 0)

    def test_rect_from_selection(self):
        """Test that we get the correct rect."""
        coords = dict(x=400, y=200, w=100, h=150)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        fake_anno = {
            'target': {
                'selector': {
                    'value': '?xywh={}'.format(coords_str)
                }
            }
        }
        rect = self.base_analyst.get_rect_from_selection_anno(fake_anno)
        assert_dict_equal(rect, coords)

    def test_rect_from_selection_with_floats(self):
        """Test that we get the correct rect with rounded coordinates."""
        coords = dict(x=400.001, y=200.499, w=100.501, h=150.999)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        fake_anno = {
            'target': {
                'selector': {
                    'value': '?xywh={}'.format(coords_str)
                }
            }
        }
        rect = self.base_analyst.get_rect_from_selection_anno(fake_anno)
        assert_dict_equal(rect, {'x': 400, 'y': 200, 'w': 101, 'h': 151})

    @with_context
    def test_get_project_template(self):
        """Test that the correct template is returned."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl1 = tmpl_fixtures.create()
        tmpl2 = tmpl_fixtures.create()
        fake_templates = [
            tmpl1.to_dict(),
            tmpl2.to_dict()
        ]
        cat_info = dict(templates=fake_templates)
        CategoryFactory.create(info=cat_info)
        project_info = dict(template_id=tmpl1.id)
        project = ProjectFactory(info=project_info)
        returned_tmpl = self.base_analyst.get_project_template(project)
        assert_equal(returned_tmpl.to_dict(), tmpl1.to_dict())

    @with_context
    @raises(ValueError)
    def test_get_invalid_project_template(self):
        """Test that getting an invalid template throws an error."""
        fake_templates = [{'id': 'foo'}]
        user_info = dict(templates=fake_templates)
        project_info = dict(template_id='bar')
        UserFactory.create(info=user_info)
        project = ProjectFactory(info=project_info)
        self.base_analyst.get_project_template(project)

    @with_context
    @raises(ValueError)
    def test_get_non_existant_project_template(self):
        """Test that getting a non-existant template throws an error."""
        project = ProjectFactory()
        self.base_analyst.get_project_template(project)

    def test_dataframe_keys_replaced(self):
        """Test that dataframe keys are replaced and columns merged."""
        data = [
            {
                'foo': 'bar',
                'baz': 'qux'
            },
            {
                'foo': 'bar',
                'quux': 'qux'
            }
        ]
        old_df = pandas.DataFrame(data, range(len(data)))
        new_df = self.base_analyst.replace_df_keys(old_df, quux='baz')
        assert_dict_equal(new_df.to_dict(), {
            'foo': {0: 'bar', 1: 'bar'},
            'baz': {0: 'qux', 1: 'qux'}
        })

    @with_context
    @patch('pybossa_lc.analysis.base.send_mail')
    @patch('pybossa_lc.analysis.base.render_template')
    @patch('pybossa_lc.analysis.base.Queue.enqueue')
    def test_comment_annotations_emailed(self, mock_enqueue, mock_render,
                                         mock_send_mail):
        """Test that comment annotation emails are sent."""
        mock_render.return_value = True
        comment = 'foo'
        creator = 'bar'
        target = 'example.com'
        fake_anno = {
            'creator': {
                'id': 'example.com/user1',
                'type': 'Person',
                'name': creator,
                'nickname': 'nick'
            },
            'body': {
                'type': 'TextualBody',
                'purpose': 'commenting',
                'value': comment,
                'format': 'text/plain'
            }
        }
        task = self.ctx.create_task(1, target)
        json_anno = json.dumps(fake_anno, indent=2, sort_keys=True)
        self.base_analyst.email_comment_anno(task, fake_anno)

        expected_render_args = [
            call('/account/email/new_comment_anno.md', annotation=json_anno,
                 creator=creator, comment=comment, raw_image=None,
                 link=None),
            call('/account/email/new_comment_anno.html', annotation=json_anno,
                 creator=creator, comment=comment, raw_image=None,
                 link=None)
        ]
        assert_equal(mock_render.call_args_list, expected_render_args)

        expected_msg = {
            'body': True,
            'html': True,
            'subject': 'New Comment Annotation',
            'recipients': flask_app.config.get('ADMINS')
        }
        mock_enqueue.assert_called_once_with(mock_send_mail, expected_msg)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_modified_results_not_updated(self, mock_client):
        """Test results are not updated if an Annotation has been modified."""
        task = self.ctx.create_task(1)
        TaskRunFactory(task=task)
        result = self.result_repo.get_by(task_id=task.id)
        self.base_analyst.analyse(result.id)
        mock_client.search_annotations.return_value = [{
            'modified': 'fake-time'
        }]
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_modified_results_not_updated(self, mock_client):
        """Test results are not updated if an Annotation has been modified."""
        task = self.ctx.create_task(1)
        TaskRunFactory(task=task)
        result = self.result_repo.get_by(task_id=task.id)
        result.info = dict(has_children=True)
        self.result_repo.update(result)
        self.base_analyst.analyse(result.id)
        assert_equal(mock_client.create_annotation.called, False)

    @with_context
    @patch('pybossa_lc.model.base.wa_client')
    def test_result_with_child_not_updated(self, mock_client):
        """Test that a result is not updated when it has a child."""
        task = self.ctx.create_task(1)
        TaskRunFactory(task=task)
        result = self.result_repo.get_by(task_id=task.id)
        info = dict(annotations='foo', has_children=True)
        result.info = info
        self.result_repo.update(result)
        self.base_analyst.analyse(result.id)
        assert_equal(result.info, info)

    @with_context
    def test_analysis_exception_if_no_annotation_collection(self):
        """Test that AnnotationCollection must be setup."""
        task = self.ctx.create_task(1, 'example.com', anno_collection=None)
        TaskRunFactory.create(task=task)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        assert_raises(AnalysisException, self.base_analyst.analyse, result.id)
