# -*- coding: utf8 -*-
"""Template model for pybossa-lc"""
from pybossa.model import make_uuid


class ProjectTemplate(object):

    def __init__(self, name, description, objective, guidance, tag, tutorial,
                 mode=None, fields=None):
        self.id = make_uuid()
        self.name = name
        self.description = description
        self.objective = objective
        self.guidance = guidance
        self.tag = tag
        self.tutorial = tutorial
        self.mode = mode
        self.fields = fields
