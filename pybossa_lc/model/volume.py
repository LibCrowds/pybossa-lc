# -*- coding: utf8 -*-
"""Volume model."""

import json
from pybossa.model import make_timestamp, make_uuid


class Volume(object):

    def __init__(self, **kwargs):
        self.id = make_uuid()
        self.name = kwargs['name']
        self.short_name = kwargs['short_name']
        self.importer = kwargs['importer']
        self.data = kwargs.get('data', {})

    def to_dict(self):
        """Return a dict representation of the object."""
        return vars(self)

    def update(self, new_data):
        """Update the object from a dict."""
        for key, value in new_data.items():
            setattr(self, key, value)
