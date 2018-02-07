# -*- coding: utf8 -*-
"""Volume exporter module for pybossa-lc."""

from pybossa.exporter import Exporter


class VolumeExporter(Exporter):

    def __init__(self):
        super(VolumeExporter, self)

    def _container(self, volume):
        return "category_{}".format(volume.category_id)
