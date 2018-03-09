# -*- coding: utf8 -*-
"""Test analysis helpers."""

import numpy
import pandas
from mock import patch, call
from freezegun import freeze_time
from factories import TaskFactory, TaskRunFactory, ProjectFactory, UserFactory
from factories import CategoryFactory
from default import db, Test, with_context, flask_app
from nose.tools import *
from pybossa.core import result_repo, task_repo
from pybossa.repositories import ResultRepository, TaskRepository
from pybossa.repositories import ProjectRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.analysis import Analyst


class TestAnalyst(Test):

    def setUp(self):
        super(TestAnalyst, self).setUp()
        Analyst.__abstractmethods__ = frozenset()
        self.analyst = Analyst()
        self.project_repo = ProjectRepository(db)
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)

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

    @with_context
    @patch("pybossa_lc.analysis.Analyst.analyse")
    def test_analyse_all(self, mock_analyse):
        """Test that all results are analysed."""
        project = ProjectFactory()
        tasks = TaskFactory.create_batch(2, project=project, n_answers=1)
        for task in tasks:
            TaskRunFactory.create(task=task)
        result = self.result_repo.get_by(task_id=tasks[0].id)
        result.info = dict(annotations=[{}])
        self.result_repo.update(result)
        self.analyst.analyse_all(project.id)
        expected = [call(t.id) for t in tasks]
        assert_equal(mock_analyse.call_args_list, expected)

    @with_context
    @patch("pybossa_lc.analysis.Analyst.analyse")
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
        self.analyst.analyse_empty(project.id)
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
        df = self.analyst.drop_keys(df, excluded)
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
        df = self.analyst.drop_empty_rows(df)
        assert_equals(df['foo'].tolist(), ['bar'])

    @with_context
    def test_partial_rows_not_dropped(self):
        """Test partial rows are not dropped."""
        data = [{
            'foo': 'bar',
            'baz': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = self.analyst.drop_empty_rows(df)
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
        has_matches = self.analyst.has_n_matches(min_answers, df)
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
        has_matches = self.analyst.has_n_matches(min_answers, df)
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
        has_matches = self.analyst.has_n_matches(min_answers, df)
        assert_equal(has_matches, True)

    @with_context
    def test_get_dataframe_with_dict(self):
        """Test the task run dataframe with a dict as the info."""
        info = {'foo': 'bar'}
        taskrun = TaskRunFactory.create(info=info)
        df = self.analyst.get_task_run_df(taskrun.task_id)
        assert_equal(df['foo'].tolist(), [info['foo']])
        assert_equal(df['info'].tolist(), [info])

    @with_context
    def test_get_dataframe_with_list(self):
        """Test the task run dataframe with a list as the info."""
        info = [{'foo': 'bar'}, {'baz': 'qux'}]
        taskrun = TaskRunFactory.create(info=info)
        df = self.analyst.get_task_run_df(taskrun.task_id)
        assert_equal(df['info'].tolist(), [info])

    @with_context
    def test_protected_keys_prefixed_when_exploded(self):
        """Test that protected info keys are prefixed."""
        info = {'foo': 'bar', 'info': 'baz'}
        taskrun = TaskRunFactory.create(info=info)
        df = self.analyst.get_task_run_df(taskrun.task_id)
        assert_equal(df['_info'].tolist(), [info['info']])

    @with_context
    def test_user_ids_in_task_run_dataframe(self):
        """Test that user IDs are included in the task run dataframe."""
        taskrun = TaskRunFactory.create()
        df = self.analyst.get_task_run_df(taskrun.task_id)
        assert_equal(df['user_id'].tolist(), [taskrun.user_id])

    def test_titlecase_normalisation(self):
        """Test titlecase normalisation."""
        rules = dict(case='title')
        norm = self.analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'Some Words')

    def test_lowercase_normalisation(self):
        """Test lowercase normalisation."""
        rules = dict(case='lower')
        norm = self.analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'some words')

    def test_uppercase_normalisation(self):
        """Test uppercase normalisation."""
        rules = dict(case='upper')
        norm = self.analyst.normalise_transcription('Some words', rules)
        assert_equal(norm, 'SOME WORDS')

    def test_whitespace_normalisation(self):
        """Test whitespace normalisation."""
        rules = dict(whitespace='normalise')
        norm = self.analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two Words')

    def test_whitespace_replace_underscore(self):
        """Test replacing whitespace with underscore normalisation."""
        rules = dict(whitespace='underscore')
        norm = self.analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two_Words')

    def test_whitespace_replace_full_stop(self):
        """Test replacing whitespace with full stop normalisation."""
        rules = dict(whitespace='full_stop')
        norm = self.analyst.normalise_transcription(' Two  Words', rules)
        assert_equal(norm, 'Two.Words')

    def test_trim_punctuation_normalisation(self):
        """Test trim punctuation normalisation."""
        rules = dict(trim_punctuation=True)
        norm = self.analyst.normalise_transcription(':Oh, a word.', rules)
        assert_equal(norm, 'Oh, a word')

    def test_date_conversion(self):
        """Test date conversion."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.analyst.normalise_transcription('19/11/1984', rules)
        assert_equal(norm, '1984-11-19')

    def test_date_conversion_with_invalid_date(self):
        """Test date conversion with invalid date."""
        rules = dict(date_format=True, dayfirst=True)
        norm = self.analyst.normalise_transcription('Not a date', rules)
        assert_equal(norm, '')

    @with_context
    def test_n_answers_increased_when_task_complete(self):
        """Test n answers required for a task is updated."""
        n_original_answers = 1
        task = TaskFactory.create(n_answers=n_original_answers)
        TaskRunFactory.create(task=task)
        self.analyst.update_n_answers_required(task)
        assert_equal(task.n_answers, n_original_answers + 1)
        assert_equal(task.state, 'ongoing')

    @with_context
    def test_n_answers_not_increased_when_still_task_runs(self):
        """Test n answers not updated when task runs still required."""
        n_original_answers = 2
        task = TaskFactory.create(n_answers=n_original_answers)
        TaskRunFactory.create(task=task)
        self.analyst.update_n_answers_required(task)
        assert_equal(task.n_answers, n_original_answers)
        assert_equal(task.state, 'ongoing')

    @with_context
    def test_n_answers_not_increased_when_max_answers_reached(self):
        """Test n answers not updated when max answers reached."""
        n_original_answers = 3
        task = TaskFactory.create(n_answers=n_original_answers)
        TaskRunFactory.create_batch(n_original_answers, task=task)
        self.analyst.update_n_answers_required(task,
                                               max_answers=n_original_answers)
        assert_equal(task.n_answers, n_original_answers)
        assert_equal(task.state, 'completed')

    def test_overlap_ratio_is_1_with_equal_rects(self):
        """Test for an overlap ratio of 1."""
        rect = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        overlap = self.analyst.get_overlap_ratio(rect, rect)
        assert_equal(overlap, 1)

    def test_overlap_ratio_is_0_with_adjacent_rects(self):
        """Test for an overlap ratio of 0."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 100, 'y': 201, 'w': 100, 'h': 100}
        overlap = self.analyst.get_overlap_ratio(r1, r2)
        assert_equal(overlap, 0)

    def test_overlap_ratio_with_partially_overlapping_rects(self):
        """Test for an overlap ratio of 0.33."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 150, 'y': 100, 'w': 100, 'h': 100}
        overlap = self.analyst.get_overlap_ratio(r1, r2)
        assert_equal('{:.2f}'.format(overlap), '0.33')

    def test_overlap_ratio_where_union_is_zero(self):
        """Test for an overlap ratio where the union is zero."""
        r1 = {'x': 0, 'y': 0, 'w': 100, 'h': 100}
        r2 = {'x': 101, 'y': 0, 'w': 100, 'h': 100}
        overlap = self.analyst.get_overlap_ratio(r1, r2)
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
        rect = self.analyst.get_rect_from_selection_anno(fake_anno)
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
        rect = self.analyst.get_rect_from_selection_anno(fake_anno)
        assert_dict_equal(rect, {'x': 400, 'y': 200, 'w': 101, 'h': 151})

    @freeze_time("19-11-1984")
    def test_get_xsd_datetime(self):
        """Test that a timestamp is returned in the correct format."""
        ts = self.analyst.get_xsd_datetime()
        assert_equal(ts, '1984-11-19T00:00:00Z')

    @with_context
    def test_get_project_template(self):
        """Test that the correct template is returned."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl1 = tmpl_fixtures.create_template()
        tmpl2 = tmpl_fixtures.create_template()
        fake_templates = [
            tmpl1.to_dict(),
            tmpl2.to_dict()
        ]
        cat_info = dict(templates=fake_templates)
        CategoryFactory.create(info=cat_info)
        project_info = dict(template_id=tmpl1.id)
        project = ProjectFactory(info=project_info)
        returned_tmpl = self.analyst.get_project_template(project.id)
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
        self.analyst.get_project_template(project.id)

    @with_context
    @raises(ValueError)
    def test_get_non_existant_project_template(self):
        """Test that getting a non-existant template throws an error."""
        project = ProjectFactory()
        self.analyst.get_project_template(project.id)

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
        new_df = self.analyst.replace_df_keys(old_df, quux='baz')
        assert_dict_equal(new_df.to_dict(), {
            'foo': {0: 'bar', 1: 'bar'},
            'baz': {0: 'qux', 1: 'qux'}
        })

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_project_template')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_describing_anno")
    def test_modified_annotations_are_not_updated(self,
                                                  mock_create_desc_anno,
                                                  mock_get_tmpl,
                                                  mock_get_tags,
                                                  mock_get_transcriptions_df,
                                                  mock_get_comments):
        """Test that a manually modified result is not updated."""
        category = CategoryFactory()
        tmpl_fixtures = TemplateFixtures(category)
        tmpl = tmpl_fixtures.create_template()
        n_answers = 3
        tmpl.min_answers = n_answers
        mock_get_tmpl.return_value = tmpl
        project = ProjectFactory.create()
        target = 'example.com'
        current_value = 'foo'
        current_tag = 'bar'
        new_value = 'baz'
        new_tag = 'qux'
        task_info = dict(target=target)
        task = TaskFactory.create(n_answers=n_answers, project=project,
                                  info=task_info)
        TaskRunFactory.create_batch(n_answers, task=task, info={
            new_value: new_value,
            current_tag: current_value
        })
        original_answer = dict(annotations=[
            {
                "motivation": "describing",
                "body": [
                    {
                        "type": "TextualBody",
                        "purpose": "describing",
                        "value": current_value,
                        "format": "text/plain",
                        "modified": "2015-01-29T09:00:00Z"
                    },
                    {
                        "type": "TextualBody",
                        "purpose": "tagging",
                        "value": current_tag
                    }
                ]
            }
        ])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        result.info = original_answer
        self.result_repo.update(result)
        data = {
            new_tag: [new_value] * n_answers,
            current_tag: [current_value] * n_answers
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        mock_create_desc_anno.return_value = {}
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 2)
        mock_create_desc_anno.assert_called_once_with(target, new_value,
                                                      new_tag)

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_describing_anno")
    def test_transcriptions_are_normalised(self,
                                           mock_create_desc_anno,
                                           mock_get_tags,
                                           mock_get_transcriptions_df,
                                           mock_get_comments):
        """Test transcriptions are normalised according to set rules."""
        n_answers = 3
        target = 'example.com'
        tag = 'foo'
        task = self.create_task_with_context(n_answers, target)
        data = {
            tag: ['OR 123  456.', 'Or.123.456. ', 'or 123 456']
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        mock_create_desc_anno.return_value = {}
        for value in data[tag]:
            TaskRunFactory.create(task=task, info={
                tag: value
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        expected = 'Or.123.456'
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_desc_anno.assert_called_once_with(target, expected, tag)

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    def test_empty_results(self,
                           mock_get_tags,
                           mock_get_transcriptions_df,
                           mock_get_comments):
        """Test that an empty result is updated correctly."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        tag = 'foo'
        data = {
            tag: [''] * n_answers
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        for value in data[tag]:
            TaskRunFactory.create(task=task, info={
                tag: value
            })
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(result.info, {
            'annotations': []
        })

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_commenting_anno")
    def test_comment_annotation_created(self,
                                        mock_create_comment_anno,
                                        mock_get_tags,
                                        mock_get_transcriptions_df,
                                        mock_get_comments):
        """Test that a comment annotation is created during analysis."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        user_id = 1
        value = 'foo'
        comment = (user_id, value)
        mock_get_comments.return_value = [comment]
        mock_create_comment_anno.return_value = {}
        TaskRunFactory.create_batch(n_answers, task=task, info={})
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_comment_anno.assert_called_once_with(target, value,
                                                         user_id)

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_describing_anno")
    def test_with_matching_transcriptions(self,
                                          mock_create_desc_anno,
                                          mock_get_tags,
                                          mock_get_transcriptions_df,
                                          mock_get_comments):
        """Test that results with matching transcriptions."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        tag1 = 'Foo'
        tag2 = 'Bar'
        val1 = 'Baz'
        val2 = 'Qux'
        TaskRunFactory.create_batch(n_answers, task=task, info={
            tag1: val1,
            tag2: val2
        })
        data = {
            tag1: [val1] * n_answers,
            tag2: [val2] * n_answers
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        mock_create_desc_anno.return_value = {}
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 2)
        call_args_list = mock_create_desc_anno.call_args_list
        assert_equal(len(call_args_list), 2)
        assert_in(call(target, val1, tag1), call_args_list)
        assert_in(call(target, val2, tag2), call_args_list)

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    def test_results_with_non_matching_answers(self,
                                               mock_get_tags,
                                               mock_get_transcriptions_df,
                                               mock_get_comments):
        """Test results with non-matching answers are updated correctly."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        tag1 = 'foo'
        tag2 = 'bar'
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                tag1: i,
                tag2: i
            })
        data = {
            tag1: range(n_answers),
            tag2: range(n_answers)
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(result.info['annotations'], [])

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_tagging_anno")
    def test_equal_regions_combined(self,
                                    mock_create_tagging_anno,
                                    mock_get_tags,
                                    mock_get_transcriptions_df,
                                    mock_get_comments):
        """Test that equal regions are combined."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        rect = dict(x=400, y=200, w=100, h=150)
        tag = 'foo'
        mock_get_tags.return_value = {
            tag: [rect] * n_answers
        }
        mock_create_tagging_anno.return_value = {}
        expected_target = {
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'],
                                                        rect['w'], rect['h'])
            }
        }
        TaskRunFactory.create_batch(n_answers, task=task)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_tagging_anno.assert_called_once_with(expected_target, tag)

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_tagging_anno")
    def test_similar_regions_combined(self,
                                      mock_create_tagging_anno,
                                      mock_get_tags,
                                      mock_get_transcriptions_df,
                                      mock_get_comments):
        """Test that similar regions are combined."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        rect1 = dict(x=90, y=100, w=110, h=90)
        rect2 = dict(x=100, y=110, w=90, h=100)
        rect3 = dict(x=110, y=90, w=100, h=110)
        tag = 'foo'
        mock_get_tags.return_value = {
            tag: [rect1, rect2, rect3]
        }
        mock_create_tagging_anno.return_value = {}
        expected_target = {
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh=90,90,120,110'
            }
        }
        TaskRunFactory.create_batch(n_answers, task=task)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 1)
        mock_create_tagging_anno.assert_called_once_with(expected_target, tag)

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    @patch("pybossa_lc.analysis.z3950.Analyst.create_tagging_anno")
    def test_different_regions_not_combined(self,
                                            mock_create_tagging_anno,
                                            mock_get_tags,
                                            mock_get_transcriptions_df,
                                            mock_get_comments):
        """Test that different regions are not combined."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target)
        tag = 'foo'
        rect1 = dict(x=10, y=10, w=10, h=10)
        rect2 = dict(x=100, y=100, w=100, h=100)
        rect3 = dict(x=200, y=200, w=200, h=200)
        rects = [rect1, rect2, rect3]
        mock_get_tags.return_value = {
            tag: rects
        }
        mock_create_tagging_anno.return_value = {}
        expected_targets = [{
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'],
                                                        rect['w'], rect['h'])
            }
        } for rect in rects]
        TaskRunFactory.create_batch(n_answers, task=task)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        assert_equal(len(result.info['annotations']), 3)
        call_args_list = mock_create_tagging_anno.call_args_list
        expected_calls = [call(expected_targets[i], tag)
                          for i in range(n_answers)]
        assert_equal(call_args_list, expected_calls)

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    def test_redundancy_increased_when_not_max(self,
                                               mock_get_tags,
                                               mock_get_transcriptions_df,
                                               mock_get_comments):
        """Test that redundancy is updated when max not reached."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target, max_answers=4)
        tag = 'Foo'
        val = 'Bar'
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                tag: val
            })
        data = {
            tag: ['{}{}'.format(val, i) for i in range(n_answers)],
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(result.info['annotations'], [])
        assert_equal(updated_task.n_answers, n_answers + 1)

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    def test_redundancy_not_increased_when_max(self,
                                               mock_get_tags,
                                               mock_get_transcriptions_df,
                                               mock_get_comments):
        """Test that redundancy is not updated when max is reached."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target,
                                             max_answers=n_answers)
        tag = 'Foo'
        val = 'Bar'
        for i in range(n_answers):
            TaskRunFactory.create(task=task, info={
                tag: val
            })
        data = {
            tag: ['{}{}'.format(val, i) for i in range(n_answers)],
        }
        mock_get_transcriptions_df.return_value = pandas.DataFrame(data)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(result.info['annotations'], [])
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    @freeze_time("19-11-1984")
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_comments')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_transcriptions_df')
    @patch('pybossa_lc.analysis.iiif_annotation.Analyst.get_tags')
    def test_redundancy_not_increased(self,
                                      mock_get_tags,
                                      mock_get_transcriptions_df,
                                      mock_get_comments):
        """Test that redundancy is not updated for non-transcriptions."""
        n_answers = 3
        target = 'example.com'
        task = self.create_task_with_context(n_answers, target, max_answers=4)
        TaskRunFactory.create_batch(n_answers, task=task)
        mock_get_transcriptions_df.return_value = pandas.DataFrame({})
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        self.analyst.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(result.info['annotations'], [])
        assert_equal(updated_task.n_answers, n_answers)

    @with_context
    def test_get_generator(self):
        """Test that the correct annotation generator is returned."""
        generator = self.analyst.get_anno_generator()
        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        github_repo = flask_app.config.get('GITHUB_REPO')
        assert_dict_equal(generator, {
            "id": github_repo,
            "type": "Software",
            "name": "LibCrowds",
            "homepage": spa_server_name
        })

    @with_context
    def test_get_creator(self):
        """Test that the correct annotation creator is returned."""
        name = 'foo'
        fullname = 'bar'
        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        user = UserFactory.create(name=name, fullname=fullname)
        url = '{}/api/user/{}'.format(spa_server_name.rstrip('/'), user.id)
        creator = self.analyst.get_anno_creator(1)
        assert_dict_equal(creator, {
            'id': url,
            'type': 'Person',
            'name': fullname,
            'nickname': name
        })

    @with_context
    @freeze_time("19-11-1984")
    def test_create_commenting_anno(self):
        """Test that a commenting annotation is created correctly."""
        name = 'foo'
        fullname = 'bar'
        target = 'baz'
        value = 'qux'
        github_repo = flask_app.config.get('GITHUB_REPO')
        spa_server_name = flask_app.config.get('SPA_SERVER_NAME')
        user = UserFactory.create(name=name, fullname=fullname)
        url = '{}/api/user/{}'.format(spa_server_name.rstrip('/'), user.id)
        anno = self.analyst.create_commenting_anno(target, value, user.id)
        print anno
        assert_dict_equal(anno, {
            '@context': 'http://www.w3.org/ns/anno.jsonld',
            'motivation': 'commenting',
            'type': 'Annotation',
            'generated': '1984-11-19T00:00:00Z',
            'created': '1984-11-19T00:00:00Z',
            'generator': {
                "id": github_repo,
                "type": "Software",
                "name": "LibCrowds",
                "homepage": spa_server_name
            },
            'creator': {
                'id': url,
                'type': 'Person',
                'name': fullname,
                'nickname': name
            },
            'body': {
                'type': 'TextualBody',
                'purpose': 'commenting',
                'value': value,
                'format': 'text/plain'
            },
            'target': target
        })
