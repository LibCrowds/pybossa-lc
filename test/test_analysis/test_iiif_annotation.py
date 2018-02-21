# -*- coding: utf8 -*-
"""Test IIIF Annotation analyst."""

import pandas
from nose.tools import *
from default import Test

from pybossa_lc.analysis.iiif_annotation import IIIFAnnotationAnalyst


class TestIIIFAnnotationAnalyst(Test):

    def setUp(self):
        super(TestIIIFAnnotationAnalyst, self).setUp()
        self.iiif_analyst = IIIFAnnotationAnalyst()
        self.comments = ['Some comment']
        self.tags = {
            'foo': [
                dict(x=100, y=100, w=100, h=100),
                dict(x=200, y=200, w=200, h=200)
            ],
            'bar': [
                dict(x=300, y=300, w=300, h=300)
            ]
        }
        transcription_data = {
            'foo': ['bar', 'baz'],
            'qux': ['quux', 'quuz']
        }
        self.transcriptions_df = pandas.DataFrame(transcription_data)

        comment_annos = []
        for comment in self.comments:
            comment_annos.append({
                'motivation': 'commenting',
                'body': {
                    'type': 'TextualBody',
                    'value': comment,
                    'purpose': 'commenting',
                    'format': 'text/plain'
                },
                'target': 'example.com'
            })

        tagging_annos = []
        for tag, rect_list in self.tags.items():
            for rect in rect_list:
                tagging_annos.append({
                    'motivation': 'tagging',
                    'body': {
                        'type': 'TextualBody',
                        'purpose': 'tagging',
                        'value': tag
                    },
                    'target': {
                        'source': 'example.com',
                        'selector': {
                            'conformsTo': 'http://www.w3.org/TR/media-frags/',
                            'type': 'FragmentSelector',
                            'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                                    rect['y'],
                                                                    rect['w'],
                                                                    rect['h'])
                        }
                    }
                })

        transcription_annos = []
        for tag, value_list in transcription_data.items():
            for value in value_list:
                transcription_annos.append({
                    'motivation': 'describing',
                    'body': [
                        {
                            'type': 'TextualBody',
                            'purpose': 'tagging',
                            'value': tag
                        },
                        {
                            'type': 'TextualBody',
                            'purpose': 'describing',
                            'value': value,
                            'format': 'text/plain'
                        }
                    ],
                    'target': 'example.com'
                })

        self.data = {
            'info': [
                comment_annos,
                tagging_annos,
                transcription_annos
            ]
        }

    def test_get_comments(self):
        """Test IIIF Annotation comments are returned."""
        task_run_df = pandas.DataFrame(self.data)
        comments = self.iiif_analyst.get_comments(task_run_df)
        assert_equal(comments, self.comments)

    def test_get_tags(self):
        """Test IIIF Annotation tags are returned."""
        task_run_df = pandas.DataFrame(self.data)
        tags = self.iiif_analyst.get_tags(task_run_df)
        assert_dict_equal(tags, self.tags)

    def test_get_transcriptions_df(self):
        """Test IIIF Annotation transcriptions are returned."""
        task_run_df = pandas.DataFrame(self.data)
        df = self.iiif_analyst.get_transcriptions_df(task_run_df)
        assert_dict_equal(df.to_dict(), self.transcriptions_df.to_dict())

    # @with_context
    # @freeze_time("19-11-1984")
    # @patch('pybossa_lc.analysis.iiif_annotation.helpers.get_project_template')
    # def test_redundancy_increased(self, mock_get_tmpl):
    #     """Test that redundancy is updated for non-matching transcriptions."""
    #     category = CategoryFactory()
    #     tmpl_fixtures = TemplateFixtures(category)
    #     tmpl = tmpl_fixtures.create_template()
    #     mock_get_tmpl.return_value = tmpl
    #     project = ProjectFactory.create()
    #     n_answers = 2
    #     task = TaskFactory.create(project=project, n_answers=n_answers)
    #     title1 = 'The Devils to Pay'
    #     title2 = 'The Devil to Pay'
    #     fake_anno1 = {
    #         'motivation': 'describing',
    #         'body': [
    #             {
    #                 "type": "TextualBody",
    #                 "purpose": "describing",
    #                 "value": title1,
    #                 "format": "text/plain"
    #             },
    #             {
    #                 "type": "TextualBody",
    #                 "purpose": "tagging",
    #                 "value": 'title'
    #             }
    #         ]
    #     }
    #     fake_anno2 = {
    #         'motivation': 'describing',
    #         'body': [
    #             {
    #                 "type": "TextualBody",
    #                 "purpose": "describing",
    #                 "value": title2,
    #                 "format": "text/plain"
    #             },
    #             {
    #                 "type": "TextualBody",
    #                 "purpose": "tagging",
    #                 "value": 'title'
    #             }
    #         ]
    #     }
    #     TaskRunFactory.create(task=task, info=[fake_anno1])
    #     TaskRunFactory.create(task=task, info=[fake_anno2])
    #     result = self.result_repo.filter_by(project_id=task.project_id)[0]
    #     iiif_annotation.analyse(result.id)
    #     updated_task = self.task_repo.get_task(task.id)
    #     assert_equal(result.info['annotations'], [])
    #     assert_equal(updated_task.n_answers, n_answers + 1)

    # @with_context
    # def test_set_target_from_selection_parent(self):
    #     """Test target set from a selection parent."""
    #     rect = dict(x=1, y=2, width=3, height=4)
    #     info = dict(highlights=[rect])
    #     task = TaskFactory.create(n_answers=1, info=info)
    #     target = 'http://example.com'
    #     anno = {
    #         'target': target
    #     }
    #     iiif_annotation.set_target_from_selection_parent(anno, task)
    #     assert_dict_equal(anno['target'], {
    #         'source': target,
    #         'selector': {
    #             'conformsTo': 'http://www.w3.org/TR/media-frags/',
    #             'type': 'FragmentSelector',
    #             'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
    #                                                     rect['y'],
    #                                                     rect['width'],
    #                                                     rect['height'])
    #         }
    #     })
