# -*- coding: utf8 -*-

from pybossa.core import db

from .analysis.analyst import Analyst
from .repositories.project_template import ProjectTemplateRepository


__all__ = ['analyst', 'project_tmpl_repo']

# Analyst
analyst = Analyst()

# Repositories
project_tmpl_repo = ProjectTemplateRepository(db)
