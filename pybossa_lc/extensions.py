# -*- coding: utf8 -*-

from pybossa.core import db

from .analysis.z3950 import Z3950Analyst
from .analysis.iiif_annotation import IIIFAnnotationAnalyst
from .repositories.project_template import ProjectTemplateRepository


__all__ = ['z3950_analyst', 'iiif_annotation_analyst', 'project_tmpl_repo']

# Analysts
z3950_analyst = Z3950Analyst()
iiif_annotation_analyst = IIIFAnnotationAnalyst()

# Repositories
project_tmpl_repo = ProjectTemplateRepository(db)
