# -*- coding: utf8 -*-
"""Volume exporter module for pybossa-lc."""

from pybossa.exporter import Exporter
from werkzeug.utils import secure_filename


class VolumeExporter(Exporter):

    def __init__(self):
        super(VolumeExporter, self)

    def _container(self, volume):
        return "category_{}".format(volume.category_id)

    def download_name(self, volume, ty, _format):
        """Overwrite the download name method for volumes."""
        name = self._project_name_latin_encoded(volume)
        filename = '%s_%s_%s.zip' % (name, ty, _format)
        filename = secure_filename(filename)
        return filename
