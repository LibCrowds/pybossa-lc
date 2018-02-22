# -*- coding: utf8 -*-
"""Main package for pybossa-lc."""

import os
import json
from flask import current_app as app
from flask.ext.plugins import Plugin
from .importers.iiif import BulkTaskIIIFImporter
from pybossa.extensions import importer
from pybossa.core import project_repo

from . import default_settings
from .extensions import *
from .jobs import queue_startup_jobs

__plugin__ = "PyBossaLC"
__version__ = json.load(open(os.path.join(os.path.dirname(__file__),
                                          'info.json')))['version']


class PyBossaLC(Plugin):
    """A PYBOSSA plugin for managing LibCrowds projects."""

    def setup(self):
        """Setup plugin."""
        self.configure()
        self.setup_blueprints()
        self.setup_iiif_importer()
        queue_startup_jobs()

    def configure(self):
        """Load configuration settings."""
        settings = [key for key in dir(default_settings) if key.isupper() and
                    not key.startswith('#')]
        for s in settings:
            if not app.config.get(s):
                app.config[s] = getattr(default_settings, s)

    def setup_blueprints(self):
        """Setup blueprints."""
        from .api.analysis import BLUEPRINT as analysis
        from .api.projects import BLUEPRINT as projects
        from .api.users import BLUEPRINT as users
        from .api.categories import BLUEPRINT as categories
        from .api.templates import BLUEPRINT as templates
        from .api.annotations import BLUEPRINT as annotations
        app.register_blueprint(analysis, url_prefix='/lc/analysis')
        app.register_blueprint(projects, url_prefix='/lc/projects')
        app.register_blueprint(users, url_prefix='/lc/users')
        app.register_blueprint(categories, url_prefix='/lc/categories')
        app.register_blueprint(templates, url_prefix='/lc/templates')
        app.register_blueprint(annotations, url_prefix='/lc/annotations')

    def setup_iiif_importer(self):
        """Setup the IIIF manifest importer."""
        importer._importers['iiif-annotation'] = BulkTaskIIIFImporter
