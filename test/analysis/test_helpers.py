# -*- coding: utf8 -*-
"""Test analysis helpers."""

import numpy
import pandas
from factories import TaskFactory, TaskRunFactory
from default import Test, with_context

from pybossa_lc.analysis import helpers, dataframer


class TestAnalysisHelpers(Test):

    def setup(self):
        super(TestAnalysisHelpers, self).setUp()

    @with_context
    def test_key_dropped(self):
        """Test the correct keys are dropped."""
        info = dict(foo=None, bar=None)
        taskrun = TaskRunFactory.create(info=info)
        df = dataframer.create_data_frame([taskrun])
        excluded = ['foo']
        df = helpers.drop_keys(df, excluded)
        assert 'foo' not in df.keys(), "foo should be dropped"
        assert 'bar' in df.keys(), "bar should not be dropped"

    @with_context
    def test_empty_rows_dropped(self):
        """Test empty rows are dropped."""
        taskrun1 = TaskRunFactory.create(info={ 'foo': 'bar' })
        taskrun2 = TaskRunFactory.create(info={ 'foo': None })
        df = dataframer.create_data_frame([ taskrun1, taskrun2 ])['foo']
        df = helpers.drop_empty_rows(df)
        assert list(df) == ['bar'], "empty row should be dropped"

    @with_context
    def test_partial_rows_not_dropped(self):
        """Test partial rows are not dropped."""
        info = dict(foo=None, bar='baz')
        taskrun = TaskRunFactory.create(info=info)
        df = dataframer.create_data_frame([ taskrun ])
        df = helpers.drop_empty_rows(df)
        assert df['info'].iloc[0] == info, "partial rows should not be dropped"

    @with_context
    def test_match_fails_when_percentage_not_met(self):
        """Test False is returned when match percentage not met."""
        taskrun1 = TaskRunFactory.create(info={ 'foo': 'bar' })
        taskrun2 = TaskRunFactory.create(info={ 'foo': None })
        df = dataframer.create_data_frame([ taskrun1, taskrun2 ])
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert not has_matches

    @with_context
    def test_match_fails_when_nan_cols(self):
        """Test False is returned when NaN columns."""
        taskrun = TaskRunFactory.create(info={ 'foo': None })
        df = dataframer.create_data_frame([ taskrun ])
        df = df.replace('', numpy.nan)
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert not has_matches

    @with_context
    def test_match_succeeds_when_percentage_met(self):
        """Test True returned when match percentage met."""
        taskrun1 = TaskRunFactory.create(info={ 'foo': 'bar' })
        taskrun2 = TaskRunFactory.create(info={ 'foo': 'bar' })
        df = dataframer.create_data_frame([ taskrun1, taskrun2 ])
        print df
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert has_matches
