# -*- coding: utf8 -*-
"""Test analysis helpers."""

import numpy
import pandas
from factories import TaskFactory, TaskRunFactory
from default import Test, with_context

from pybossa_lc.analysis import helpers


class TestAnalysisHelpers(Test):

    def setup(self):
        super(TestAnalysisHelpers, self).setUp()

    @with_context
    def test_key_dropped(self):
        """Test the correct keys are dropped."""
        data = [{
          'foo': None,
          'bar': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        excluded = ['foo']
        df = helpers.drop_keys(df, excluded)
        assert 'foo' not in df.keys(), "foo should be dropped"
        assert 'bar' in df.keys(), "bar should not be dropped"

    @with_context
    def test_empty_rows_dropped(self):
        """Test empty rows are dropped."""
        data = [{
          'foo': 'bar'
        },
        {
          'foo': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = helpers.drop_empty_rows(df)
        assert df['foo'].tolist() == ['bar'], "empty row should be dropped"

    @with_context
    def test_partial_rows_not_dropped(self):
        """Test partial rows are not dropped."""
        data = [{
          'foo': 'bar',
          'baz': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = helpers.drop_empty_rows(df)
        expected = {'foo': {0: 'bar'}, 'baz': {0: None}}
        assert df.to_dict() == expected, "partial rows should not be dropped"

    @with_context
    def test_match_fails_when_percentage_not_met(self):
        """Test False is returned when match percentage not met."""
        data = [{
          'foo': 'bar',
          'baz': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert not has_matches

    @with_context
    def test_match_fails_when_nan_cols(self):
        """Test False is returned when NaN columns."""
        data = [{
          'foo': None
        }]
        df = pandas.DataFrame(data, range(len(data)))
        df = df.replace('', numpy.nan)
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert not has_matches

    @with_context
    def test_match_succeeds_when_percentage_met(self):
        """Test True returned when match percentage met."""
        data = [{
          'foo': 'bar'
        },
        {
          'foo': 'bar'
        }]
        df = pandas.DataFrame(data, range(len(data)))
        has_matches = helpers.has_n_matches(df, 2, 100)
        assert has_matches
