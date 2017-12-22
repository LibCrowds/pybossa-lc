# -*- coding: utf8 -*-

import sys
import os
import pybossa_lc as plugin


# Use the PYBOSSA test settings
PB_PATH = os.environ.get('PYBOSSA_PATH', '..')
sys.path.append(os.path.abspath(os.path.join(PB_PATH, 'test')))
PYBOSSA_TEST_SETTINGS = os.path.join(PB_PATH, 'settings_test.py')


def setUpPackage():
    """Setup the plugin."""
    from default import flask_app
    with flask_app.app_context():
        pb_settings = os.path.abspath(PYBOSSA_TEST_SETTINGS)
        pb_lc_settings = os.path.abspath('settings_test.py')
        flask_app.config.from_pyfile(pb_settings)
        flask_app.config.from_pyfile(pb_lc_settings)
        plugin_dir = os.path.dirname(plugin.__file__)
        plugin.PyBossaLC(plugin_dir).setup()
