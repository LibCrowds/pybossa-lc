# -*- coding: utf8 -*-
"""IIIF Annotation analysis module."""

import pandas
import itertools

from . import Analyst


class IIIFAnnotationAnalyst(Analyst):

    def get_comments(self, task_run_df):
        """Return a list of comments."""
        comments = []
        for _index, row in task_run_df.iterrows():
            user_id = row['user_id']
            annotations = row['info']
            for anno in annotations:
                if anno['motivation'] == 'commenting':
                    item = (user_id, anno['body']['value'])
                    comments.append(item)
        return comments

    def get_tags(self, task_run_df):
        """Return a dict of tags against fragment selectors."""
        annotations = list(itertools.chain(*task_run_df['info']))
        tags = {}
        for anno in annotations:
            if anno['motivation'] == 'tagging':
                body = anno['body']
                if isinstance(body, list):
                    tag = [item['value'] for item in body
                           if item['purpose'] == 'tagging'][0]
                else:
                    tag = body['value']
                rect = self.get_rect_from_selection_anno(anno)
                tag_values = tags.get(tag, [])
                tag_values.append(rect)
                tags[tag] = tag_values
        return tags

    def get_transcriptions_df(self, task_run_df):
        """Return a dataframe of transcriptions."""
        annotations = list(itertools.chain(*task_run_df['info']))
        transcriptions = {}
        for anno in annotations:
            if anno['motivation'] == 'describing':
                tag = [body['value'] for body in anno['body']
                       if body['purpose'] == 'tagging'][0]
                value = [body['value'] for body in anno['body']
                         if body['purpose'] == 'describing'][0]
                tag_values = transcriptions.get(tag, [])
                tag_values.append(value)
                transcriptions[tag] = tag_values
        return pandas.DataFrame(transcriptions)
