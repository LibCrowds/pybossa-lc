# -*- coding: utf8 -*-
"""Main package for pybossa-lc."""

import os
import json
from flask import current_app as app
from flask.ext.plugins import Plugin
from .importers.iiif import BulkTaskIIIFImporter
from pybossa.extensions import importer

__plugin__ = "PyBossaLC"
__version__ = json.load(open(os.path.join(os.path.dirname(__file__),
                                          'info.json')))['version']


class PyBossaLC(Plugin):
    """A PYBOSSA plugin for managing LibCrowds projects."""

    def setup(self):
        """Setup plugin."""
        self.setup_blueprints()
        self.setup_iiif_importer()

    def setup_blueprints(self):
        """Setup blueprints."""
        from .api.analysis import BLUEPRINT as analysis
        from .api.results import BLUEPRINT as results
        from .api.projects import BLUEPRINT as projects
        from .api.users import BLUEPRINT as users
        app.register_blueprint(analysis, url_prefix='/libcrowds/analysis')
        app.register_blueprint(results, url_prefix='/libcrowds/results')
        app.register_blueprint(projects, url_prefix='/libcrowds/projects')
        app.register_blueprint(users, url_prefix='/libcrowds/users')

    def setup_iiif_importer(self):
        """Setup the IIIF manifest importer."""
        importer._importers['iiif-annotation'] = BulkTaskIIIFImporter
