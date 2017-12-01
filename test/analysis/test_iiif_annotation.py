# -*- coding: utf8 -*-
"""Test IIIF Annotation analysis."""

import numpy
import pandas
from freezegun import freeze_time
from mock import patch, call
from factories import TaskFactory, TaskRunFactory, ProjectFactory
from default import Test, with_context, db
from pybossa.repositories import ResultRepository

from pybossa_lc.analysis import iiif_annotation


class TestIIIFAnnotationAnalysis(Test):

    def setUp(self):
        super(TestIIIFAnnotationAnalysis, self).setUp()
        self.result_repo = ResultRepository(db)

    def test_overlap_ratio_is_1_with_equal_rects(self):
        """Test for an overlap ratio of 1."""
        rect = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        overlap = iiif_annotation.get_overlap_ratio(rect, rect)
        assert overlap == 1, "overlap should be 1"

    def test_overlap_ratio_is_0_with_adjacent_rects(self):
        """Test for an overlap ratio of 0."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 100, 'y': 201, 'w': 100, 'h': 100}
        overlap = iiif_annotation.get_overlap_ratio(r1, r2)
        assert overlap == 0, "overlap should be 0"

    def test_overlap_ratio_with_partially_overlapping_rects(self):
        """Test for an overlap ratio of 0.33."""
        r1 = {'x': 100, 'y': 100, 'w': 100, 'h': 100}
        r2 = {'x': 150, 'y': 100, 'w': 100, 'h': 100}
        overlap = iiif_annotation.get_overlap_ratio(r1, r2)
        assert '{:.2f}'.format(overlap) == '0.33', "overlap should be 0.33"

    def test_rect_from_selection(self):
        """Test that we get the correct rect."""
        coords = dict(x=400, y=200, w=100, h=150)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        fake_anno = {
            'target': {
                'selector': {
                    'value': '?xywh={}'.format(coords_str)
                }
            }
        }
        rect = iiif_annotation.get_rect_from_selection(fake_anno)
        assert rect == coords, "rect should have original coords"

    def test_rect_from_selection_with_floats(self):
        """Test that we get the correct rect with rounded coordinates."""
        coords = dict(x=400.001, y=200.499, w=100.501, h=150.999)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        fake_anno = {
            'target': {
                'selector': {
                    'value': '?xywh={}'.format(coords_str)
                }
            }
        }
        rect = iiif_annotation.get_rect_from_selection(fake_anno)
        msg = "rect should have rounded coords"
        assert rect == {'x': 400, 'y': 200, 'w': 101, 'h': 151}, msg

    @with_context
    def test_empty_result_updated(self):
        """Test that an empty result is updated correctly."""
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info=[])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert result.info == {
            'annotations': []
        }, "final annotations should be empty"

    @with_context
    @freeze_time("19-11-1984")
    def test_equal_regions_combined(self):
        """Test that equal regions are combined."""
        coords = dict(x=400, y=200, w=100, h=150)
        coords_str = '{0},{1},{2},{3}'.format(coords['x'], coords['y'],
                                              coords['w'], coords['h'])
        tr_info = [{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00',
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
        msg = "final annotations should equal tr_info"
        assert result.info == {'annotations': tr_info}, msg

    @with_context
    @freeze_time("19-11-1984")
    def test_similar_regions_combined(self):
        """Test that equal regions are combined."""
        task = TaskFactory.create(n_answers=2)
        TaskRunFactory.create(task=task, info=[{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00',
            'target': {
                'selector': {
                    'value': '?xywh=100,100,100,100'
                }
            }
        }])
        TaskRunFactory.create(task=task, info=[{
            'motivation': 'tagging',
            'modified': '1984-11-19T00:00:00',
            'target': {
                'selector': {
                    'value': '?xywh=110,110,90,90'
                }
            }
        }])
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        assert result.info == {
            'annotations': [
                {
                    'motivation': 'tagging',
                    'modified': '1984-11-19T00:00:00',
                    'target': {
                        'selector': {
                            'value': '?xywh=100,100,100,100'
                        }
                    }
                }
            ]
        }, "final annotations should contain one combined selection"

    @with_context
    @patch('pybossa_lc.analysis.iiif_annotation.analyse', return_value=True)
    def test_all_results_analysed(self, mock_analyse):
        """Test results with non-matching answers are updated correctly."""
        project = ProjectFactory.create()
        task1 = TaskFactory.create(project=project, n_answers=1)
        task2 = TaskFactory.create(project=project, n_answers=1)
        TaskRunFactory.create(task=task1)
        TaskRunFactory.create(task=task2)
        results = self.result_repo.filter_by(project_id=project.id)
        calls = [call(r) for r in results]
        iiif_annotation.analyse_all(project.id)
        assert mock_analyse.has_calls(calls, any_order=True)

    @with_context
    @freeze_time("19-11-1984")
    def test_comments_appended(self):
        """Test that comment annotations are appended."""
        tr_info = [{
            'motivation': 'commenting',
            'modified': '1984-11-19T00:00:00',
            'body': {
                'value': 'I like turtles'
            }
        }]
        task = TaskFactory.create(n_answers=1)
        TaskRunFactory.create(task=task, info=tr_info)
        result = self.result_repo.filter_by(project_id=task.project_id)[0]
        iiif_annotation.analyse(result.id)
        msg = "comment annotation should be stored"
        assert result.info == {'annotations': tr_info}, msg
