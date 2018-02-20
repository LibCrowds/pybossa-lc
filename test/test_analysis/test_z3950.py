# -*- coding: utf8 -*-
"""Test Z39.50 analyst."""

import pandas
from nose.tools import *
from default import Test

from pybossa_lc.analysis.z3950 import Z3950Analyst


class TestZ3950Analyst(Test):

    def setUp(self):
        super(TestZ3950Analyst, self).setUp()
        self.z3950_analyst = Z3950Analyst()
        self.data = {
            'control_number': ['123'],
            'reference': ['abc'],
            'foo': ['bar'],
            'comments': ['Some comment']
        }

    def test_get_comments(self):
        """Test Z3950 comments are returned."""
        task_run_df = pandas.DataFrame(self.data)
        comments = self.z3950_analyst.get_comments(task_run_df)
        assert_equal(comments, self.data['comments'])

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
