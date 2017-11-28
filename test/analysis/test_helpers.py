# -*- coding: utf8 -*-
"""Test analysis helpers."""

import numpy
import pandas
from factories import TaskFactory, TaskRunFactory
from default import Test, with_context

from pybossa_lc.analysis import helpers


class TestAnalysisHelpers(Test):

    def setUp(self):
        super(TestAnalysisHelpers, self).setUp()
        with self.flask_app.app_context():
            self.create()

    def test_drop_keys(self):
        """Test the correct keys are dropped."""
        taskrun = TaskRunFactory.create(n=42, comment='hello')
        excluded = ['n']
        df = pandas.DataFrame(taskrun)
        print df
        df = helpers.drop_keys(df, excluded)
        assert df.keys() == ['comment']

    # def test_keys_excluded(self, create_task_run_df):
    #     """Test excluded keys are not returned."""
    #     tr_info = [
    #         {'n': '42'},
    #         {'comment': 'hello'}
    #     ]
    #     excluded = ['comment']
    #     df = create_task_run_df(tr_info)
    #     df = helpers.drop_keys(df, excluded)
    #     assert df.keys() == ['n']

    # def test_empty_rows_dropped(self, create_task_run_df):
    #     """Test empty rows are dropped."""
    #     tr_info = [
    #         {'n': '42'},
    #         {'n': ''}
    #     ]
    #     df = create_task_run_df(tr_info)[['n']]
    #     df = helpers.drop_empty_rows(df)
    #     assert len(df) == 1 and df['n'][0] == '42'

    # def test_partial_rows_not_dropped(self, create_task_run_df):
    #     """Test partial rows are not dropped."""
    #     tr_info = [
    #         {'n': '42', 'comment': ''}
    #     ]
    #     df = create_task_run_df(tr_info)
    #     df = helpers.drop_empty_rows(df)
    #     assert tr_info == df['info'].tolist()

    # def test_match_fails_when_percentage_not_met(self, create_task_run_df):
    #     """Test False is returned when match percentage not met."""
    #     tr_info = [
    #         {'n': '42'},
    #         {'n': ''}
    #     ]
    #     df = create_task_run_df(tr_info)[['n']]
    #     has_matches = helpers.has_n_matches(df, 2, 100)
    #     assert not has_matches

    # def test_match_fails_when_nan_cols(self, create_task_run_df):
    #     """Test False is returned when NaN columns."""
    #     tr_info = [
    #         {'n': '', 'comment': ''}
    #     ]
    #     df = create_task_run_df(tr_info)[['n', 'comment']]
    #     df = df.replace('', numpy.nan)
    #     has_matches = helpers.has_n_matches(df, 2, 100)
    #     assert not has_matches

    # def test_match_succeeds_when_percentage_met(self, create_task_run_df):
    #     """Test True returned when match percentage met."""
    #     tr_info = [
    #         {'n': '42'},
    #         {'n': '42'}
    #     ]
    #     df = create_task_run_df(tr_info)[['n']]
    #     has_matches = helpers.has_n_matches(df, 2, 100)
    #     assert has_matches
