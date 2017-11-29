# -*- coding: utf8 -*-

import sys
import os
import pybossa_lc as plugin

# Use the PyBossa test suite
sys.path.append(os.path.abspath("./pybossa/test"))


PYBOSSA_TEST_SETTINGS = 'pybossa/settings_test.py'


def setUpPackage():
    """Setup the plugin."""
    from default import flask_app
    with flask_app.app_context():
        settings = os.path.abspath(PYBOSSA_TEST_SETTINGS)
        flask_app.config.from_pyfile(settings)
        plugin_dir = os.path.dirname(plugin.__file__)
        plugin.PyBossaLC(plugin_dir).setup()
