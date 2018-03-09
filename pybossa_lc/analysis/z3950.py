# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

from . import Analyst


MATCH_PERCENTAGE = 60


class Z3950Analyst(Analyst):

    def __init__(self):
        super(Z3950Analyst, self).__init__()
        self.required_keys = ['control_number', 'reference', 'comments']

    def get_comments(self, task_run_df):
        """Return a list of comments."""
        comments = task_run_df['comments'].tolist()
        user_ids = task_run_df['user_id'].tolist()
        return [(user_ids[i], comment) for i, comment in enumerate(comments)
                if comment]

    def get_tags(self, task_run_df):
        """Return a dict of tags against fragment selectors."""
        return {}

    def get_transcriptions_df(self, task_run_df):
        """Return a dataframe of transcriptions."""
        return task_run_df[['control_number', 'reference']]
