# -*- coding: utf8 -*-

from pybossa.core import db

from .analysis.analyst import Analyst
from .repositories.project_template import ProjectTemplateRepository
from .web_annotation_client import WebAnnotationClient


__all__ = ['analyst', 'project_tmpl_repo', 'wa_client']

# Analyst
analyst = Analyst()

# Repositories
project_tmpl_repo = ProjectTemplateRepository(db)

# Web Annotation Client
wa_client = WebAnnotationClient()
