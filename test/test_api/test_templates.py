# -*- coding: utf8 -*-
"""Test templates API."""

from mock import patch
from nose.tools import *
from helper import web
from default import with_context, db
from pybossa.repositories import ResultRepository, UserRepository

from pybossa_lc.api import analysis as analysis_api


class TestTemplatesApi(web.Helper):

    def setUp(self):
        super(TestTemplatesApi, self).setUp()
        self.result_repo = ResultRepository(db)
        self.user_repo = UserRepository(db)

@with_context
def test_results_updated_when_template_approved(self):
    pass

