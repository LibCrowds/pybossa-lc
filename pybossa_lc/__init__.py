# -*- coding: utf8 -*-
"""Main package for pybossa-lc."""

import os
import json
from flask import current_app as app
from flask.ext.plugins import Plugin

__plugin__ = "PyBossaLC"
__version__ = json.load(open(os.path.join(os.path.dirname(__file__),
                                          'info.json')))['version']


class PyBossaLC(Plugin):
    """A PYBOSSA plugin for managing LibCrowds projects."""

    def setup(self):
        """Setup plugin."""
        self.setup_blueprints()

    def setup_blueprints(self):
        """Setup blueprints."""
        from .api.analysis import BLUEPRINT as analysis_bp
        from .api.results import BLUEPRINT as results_bp
        app.register_blueprint(analysis_bp, url_prefix='/libcrowds/analysis')
        app.register_blueprint(results_bp, url_prefix='/libcrowds/results')
