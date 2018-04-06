# -*- coding: utf8 -*-
"""Analyst module."""

from .z3950 import Z3950Analyst
from .iiif_annotation import IIIFAnnotationAnalyst
from . import AnalysisException

from pybossa.jobs import project_export


class Analyst(object):

    def __init__(self):
        """Init method."""
        self._analysts = {
            'z3950': Z3950Analyst,
            'iiif-annotation': IIIFAnnotationAnalyst
        }

    def analyse(self, presenter, result_id, silent=True):
        """Analyse a single result."""
        analyst = self._analysts.get(presenter)()
        if not analyst:
            msg = 'Invalid task presenter: {}'.format(presenter)
            raise AnalysisException(msg)
        analyst.analyse(result_id, silent)

    def analyse_all(self, presenter, project_id):
        """Analyse all results."""
        analyst = self._analysts.get(presenter)()
        if not analyst:
            msg = 'Invalid task presenter: {}'.format(presenter)
            raise AnalysisException(msg)
        analyst.analyse_all(project_id)
        project_export(project_id)

    def analyse_empty(self, presenter, project_id):
        """Analyse empty results."""
        analyst = self._analysts.get(presenter)()
        if not analyst:
            msg = 'Invalid task presenter: {}'.format(presenter)
            raise AnalysisException(msg)
        analyst.analyse_empty(project_id)
        project_export(project_id)
