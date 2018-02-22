# -*- coding: utf8 -*-
"""IIIF Annotation analysis module."""

import pandas
import itertools

from . import Analyst


class IIIFAnnotationAnalyst(Analyst):

    def __init__(self):
        super(IIIFAnnotationAnalyst, self).__init__()

    def get_comments(self, task_run_df):
        """Return a list of comments."""
        annotations = list(itertools.chain(*task_run_df['info']))
        comments = []
        for anno in annotations:
            if anno['motivation'] == 'commenting':
                comments.append(anno['body']['value'])
        return comments

    def get_tags(self, task_run_df):
        """Return a dict of tags against fragment selectors."""
        annotations = list(itertools.chain(*task_run_df['info']))
        tags = {}
        for anno in annotations:
            if anno['motivation'] == 'tagging':
                tag = anno['body']['value']
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

    def set_target_from_selection_parent(self, annotation, task):
        """Set the annotation target according to a selection parent task."""
        highlights = task.info.get('highlights')
        if not highlights:
            raise ValueError('This task was not built from a selection parent')

        rect = highlights[0]
        selector = '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                  rect['y'],
                                                  rect['width'],
                                                  rect['height'])
        annotation['target'] = {
            'source': annotation['target'],
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': selector
            }
        }
