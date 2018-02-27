# -*- coding: utf8 -*-
"""Project template model."""

import json
from pybossa.model import make_timestamp, make_uuid


class ProjectTemplate(object):

    def __init__(self, **kwargs):
        self.id = make_uuid()
        self.created = make_timestamp()
        self.name = kwargs['name']
        self.description = kwargs['description']
        self.category_id = kwargs['category_id']
        self.owner_id = kwargs['owner_id']
        self.min_answers = kwargs.get('min_answers', 3)
        self.max_answers = kwargs.get('max_answers', 3)
        self.tutorial = kwargs.get('tutorial', '')
        self.task = kwargs.get('task', {})
        self.rules = kwargs.get('rules', {})
        self.pending = kwargs.get('pending', True)

    def to_dict(self):
        """Return a dict representation of the object."""
        return vars(self)

    def update(self, new_data):
        """Update the object from a dict."""
        for key, value in new_data.items():
            setattr(self, key, value)
