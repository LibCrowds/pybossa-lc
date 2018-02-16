# -*- coding: utf8 -*-
"""Test IIIF Annotation analysis."""

import numpy
import pandas
from nose.tools import *
from freezegun import freeze_time
from mock import patch, call
from factories import TaskFactory, TaskRunFactory, ProjectFactory, UserFactory
from factories import CategoryFactory
from default import Test, with_context, db
from pybossa.repositories import ResultRepository, TaskRepository

from ..fixtures import TemplateFixtures
from pybossa_lc.analysis import iiif_annotation


class TestIIIFAnnotationAnalysis(Test):

    def setUp(self):
        super(TestIIIFAnnotationAnalysis, self).setUp()
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)

    @with_context
    def test_empty_result_updated(self):
        """Test that an empty result is updated correctly."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info=[])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert_dict_equal(result.info, {'annotations': []})

    @with_context
    @freeze_time("19-11-1984")
    def test_equal_regions_combined(self):
        """Test that equal regions are combined."""
        coords = dict(x=400, y=200, w=100, h=150)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        tr_info = [{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00Z',
            'target': {
                'selector': {
                    'value': '?xywh={}'.format(coords_str)
                }
            }
        }]
        task = TaskFactory.create(n_answers=2)
        TaskRunFactory.create(task=task, info=tr_info)
        TaskRunFactory.create(task=task, info=tr_info)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert_dict_equal(result.info, {'annotations': tr_info})

    @with_context
    @freeze_time("19-11-1984")
    def test_similar_regions_combined(self):
        """Test that similar regions are combined."""
        task = TaskFactory.create(n_answers=2)
        TaskRunFactory.create(task=task, info=[{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00Z',
            'target': {
                'selector': {
                    'value': '?xywh=100,100,100,100'
                }
            }
        }])
        TaskRunFactory.create(task=task, info=[{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00Z',
            'target': {
                'selector': {
                    'value': '?xywh=110,110,90,90'
                }
            }
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert_dict_equal(result.info, {
            'annotations': [
                {
                    'motivation': 'tagging',
                    'modified': '1984-11-19T00:00:00Z',
                    'target': {
                        'selector': {
                            'value': '?xywh=100,100,100,100'
                        }
                    }
                }
            ]
        })

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.analyse', return_value=True)
    def test_all_results_analysed(self, mock_analyse):
        """Test all IIIF Annotation results analysed."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        calls = [call(r.id) for r in results]
        iiif_annotation.analyse_all(project.id)
        assert mock_analyse.has_calls(calls, any_order=True)

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.analyse', return_value=True)
    def test_empty_results_analysed(self, mock_analyse):
        """Test empty IIIF Annotation results analysed."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        results[0].info = dict(foo='bar')
        self.result_repo.update(results[0])
        iiif_annotation.analyse_empty(project.id)
        mock_analyse.assert_called_once_with(results[1].id)

    def test_merge_transcriptions(self):
        """Test that the most common transcriptions are merged."""
        tag = 'title'
        title1 = 'The Devils to Pay'
        title2 = 'The Devil to Pay'
        fake_anno1 = {
            'body': [
                {
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": title1,
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": tag
                }
            ]
        }
        fake_anno2 = {
            'body': [
                {
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": title2,
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": tag
                }
            ]
        }
        annotations = [fake_anno1, fake_anno2, fake_anno2]
        merged = iiif_annotation.merge_transcriptions(annotations, {})
        assert_dict_equal(merged, {
            tag: {
                'annotation': fake_anno2,
                'count': 2
            }
        })

    @with_context
    @freeze_time("19-11-1984")
    def test_matching_transcription_annotations_stored(self):
        """Test that matching transcriptions are stored."""
        task = TaskFactory.create(n_answers=2)
        tr_info = [{
            "motivation": "describing",
            "modified": "1984-11-19T00:00:00Z",
            "target": {
                "selector": {
                    "value": "?xywh=100,100,100,100"
                }
            },
            "body": [
                {
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": "The Devil to Pay",
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": "title"
                }
            ]
        }]
        TaskRunFactory.create_batch(2, task=task, info=tr_info)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert_equal(len(result.info['annotations']), 1)
        assert_dict_equal(result.info['annotations'][0], tr_info[0])

    @with_context
    @freeze_time("19-11-1984")
    def test_redundancy_increased_when_transcriptions_not_matching(self):
        """Test that redundancy is updated for non-matching transcriptions."""
        n_answers = 2
        task = TaskFactory.create(n_answers=n_answers)
        title1 = 'The Devils to Pay'
        title2 = 'The Devil to Pay'
        fake_anno1 = {
            'motivation': 'describing',
            'body': [
                {
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": title1,
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": 'title'
                }
            ]
        }
        fake_anno2 = {
            'motivation': 'describing',
            'body': [
                {
                    "type": "TextualBody",
                    "purpose": "describing",
                    "value": title2,
                    "format": "text/plain"
                },
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": 'title'
                }
            ]
        }
        TaskRunFactory.create(task=task, info=[fake_anno1])
        TaskRunFactory.create(task=task, info=[fake_anno2])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        updated_task = self.task_repo.get_task(task.id)
        assert_equal(result.info['annotations'], [])
        assert_equal(updated_task.n_answers, n_answers + 1)

    @with_context
    def test_set_target_from_selection_parent(self):
        """Test target set from a selection parent."""
        rect = dict(x=1, y=2, width=3, height=4)
        info = dict(highlights=[rect])
        task = TaskFactory.create(n_answers=1, info=info)
        target = 'http://example.com'
        anno = {
            'target': target
        }
        iiif_annotation.set_target_from_selection_parent(anno, task)
        assert_dict_equal(anno['target'], {
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh={0},{1},{2},{3}'.format(rect['x'],
                                                        rect['y'],
                                                        rect['width'],
                                                        rect['height'])
            }
        })
