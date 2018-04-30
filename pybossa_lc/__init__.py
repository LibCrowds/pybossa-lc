# -*- coding: utf8 -*-
"""Main package for pybossa-lc."""

import os
import json
import shutil
from distutils.dir_util import copy_tree
from flask import current_app as app
from flask.ext.plugins import Plugin
from pybossa.extensions import importer
from pybossa.core import project_repo, db

from . import default_settings
from .importers.iiif_enhanced import BulkTaskIIIFEnhancedImporter
from .extensions import *
from .jobs import enqueue_periodic_jobs


__plugin__ = "PyBossaLC"
__version__ = json.load(open(os.path.join(os.path.dirname(__file__),
                                          'info.json')))['version']


class PyBossaLC(Plugin):
    """A PYBOSSA plugin for managing LibCrowds projects."""

    def setup(self):
        """Setup plugin."""
        self.configure()
        self.setup_blueprints()
        self.replace_email_templates()
        self.setup_enhanced_iiif_importer()
        enqueue_periodic_jobs()

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
        from .api.categories import BLUEPRINT as categories
        from .api.templates import BLUEPRINT as templates
        from .api.annotations import BLUEPRINT as annotations
        from .api.admin import BLUEPRINT as admin
        from .api.users import BLUEPRINT as users
        app.register_blueprint(analysis, url_prefix='/lc/analysis')
        app.register_blueprint(projects, url_prefix='/lc/projects')
        app.register_blueprint(categories, url_prefix='/lc/categories')
        app.register_blueprint(templates, url_prefix='/lc/templates')
        app.register_blueprint(annotations, url_prefix='/lc/annotations')
        app.register_blueprint(admin, url_prefix='/lc/admin')
        app.register_blueprint(users, url_prefix='/lc/users')

    def replace_email_templates(self):
        """Replace email templates in the current theme."""
        if not app.config.get('TESTING'):
            out_path = os.path.join('pybossa', app.template_folder, 'account',
                                    'email')
            in_path = os.path.join('pybossa', 'plugins', 'pybossa_lc',
                                   'templates', 'email')
            if not os.path.exists(out_path):
                os.mkdir(out_path)
            copy_tree(in_path, out_path)

    def setup_enhanced_iiif_importer(self):
        """Setup the enhanced IIIF manifest importer."""
        importer._importers['iiif-enhanced'] = BulkTaskIIIFEnhancedImporter
