# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

from .base import BaseAnalyst
from . import AnalysisException


class Z3950Analyst(BaseAnalyst):

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
        replaced_keys = dict(shelfmark='reference', oclc='control_number')
        updated_df = self.replace_df_keys(task_run_df, **replaced_keys)
        required_keys = ['control_number', 'reference']

        if not all(key in updated_df for key in required_keys):
            msg = 'Invalid task run data: required keys are missing'
            raise AnalysisException(msg)

        return updated_df[required_keys]
