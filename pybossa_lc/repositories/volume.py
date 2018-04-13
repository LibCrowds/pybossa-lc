# -*- coding: utf8 -*-
"""Volume repository module."""

import itertools
from sqlalchemy.exc import IntegrityError
from pybossa.model.category import Category
from pybossa.exc import WrongObjectError, DBIntegrityError

from ..model.volume import Volume
from . import Repository


class VolumeRepository(Repository):

    def get(self, id):
        """Get a volume from Category context."""
        filter_dict = {'volumes': [{'id': id}]}
        category = self.db.session.query(Category).filter(
            Category.info.contains(filter_dict)
        ).first()
        if not category:
            return None

        volumes = category.info.get('volumes', [])
        vol_dict = [vol for vol in volumes if vol['id'] == id][0]
        return self._convert_to_object(vol_dict)

    def _convert_to_object(self, volume_dict):
        """Convert a volume dict to an object."""
        vol = Volume(**volume_dict)
        vol.id = volume_dict['id']
        return vol
