# -*- coding: utf8 -*-

from .analysis.z3950 import Z3950Analyst
from .analysis.iiif_annotation import IIIFAnnotationAnalyst


__all__ = ['z3950_analyst', 'iiif_annotation_analyst']


z3950_analyst = Z3950Analyst()
iiif_annotation_analyst = IIIFAnnotationAnalyst()
