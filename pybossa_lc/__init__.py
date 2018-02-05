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
        self.remove_bad_volumes()
        queue_startup_jobs()

    def configure(self):
        """Load configuration settings."""
        app.config.from_object(default_settings)


    def setup_blueprints(self):
        """Setup blueprints."""
        from .api.analysis import BLUEPRINT as analysis
        from .api.projects import BLUEPRINT as projects
        from .api.users import BLUEPRINT as users
        from .api.categories import BLUEPRINT as categories
        from .api.templates import BLUEPRINT as templates
        from .api.annotations import BLUEPRINT as annos
        app.register_blueprint(analysis, url_prefix='/libcrowds/analysis')
        app.register_blueprint(projects, url_prefix='/libcrowds/projects')
        app.register_blueprint(users, url_prefix='/libcrowds/users')
        app.register_blueprint(categories, url_prefix='/libcrowds/categories')
        app.register_blueprint(templates, url_prefix='/libcrowds/templates')
        app.register_blueprint(annos, url_prefix='/libcrowds/annotations')

    def setup_iiif_importer(self):
        """Setup the IIIF manifest importer."""
        importer._importers['iiif-annotation'] = BulkTaskIIIFImporter

    def remove_bad_volumes(self):
        """Remove volumes that don't comply with the correct data structure."""
        if app.config.get('TESTING'):
            return

        categories = project_repo.get_all_categories()
        required_keys = ['id', 'name', 'source']
        for category in categories:
            if not isinstance(category.info, dict):
                category.info = {}

            volumes = category.info.get('volumes', [])
            if not isinstance(volumes, list):
                volumes = []
                print "Invalid volumes removed for {}".format(category.name)

            valid_volumes = [v for v in volumes
                             if all(key in v.keys() for key in required_keys)]
            if len(valid_volumes) != len(volumes):
                print "Invalid volumes removed for {}".format(category.name)

            category.info['volumes'] = valid_volumes
            project_repo.update_category(category)
