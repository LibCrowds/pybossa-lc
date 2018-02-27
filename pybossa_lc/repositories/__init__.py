# -*- coding: utf8 -*-
"""Repository module."""


class Repository(object):

    def __init__(self, db):
        self.db = db


from .project_template import ProjectTemplateRepository

assert ProjectTemplateRepository
