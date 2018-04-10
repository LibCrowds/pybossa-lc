# -*- coding: utf8 -*-
"""JSON volume exporter module for pybossa-lc."""

import json
import tempfile
from collections import namedtuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.core import uploader

from .base import CustomExporterBase


class JsonCustomExporter(CustomExporterBase):

    def _respond_json(self, category_id, root_template_id, include):
        return self._get_data(category_id, root_template_id, include)

    def _make_zip(self, volume, ty):
        name = self._project_name_latin_encoded(volume)
        json_data_generator = self._respond_json(volume.id, ty)
        if json_data_generator is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                datafile.write(json.dumps(json_data_generator))
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.json' % (name, ty)
                    _zip.write(datafile.name, secure_filename(fn))
                    _zip.close()
                    container = self._container(volume)
                    dl_fn = self.download_name(volume, ty)
                    _file = FileStorage(filename=dl_fn, stream=zipped_datafile)
                    uploader.upload_file(_file, container=container)
                finally:
                    zipped_datafile.close()
            finally:
                datafile.close()

    def download_name(self, volume, ty):
        return super(JsonCustomExporter, self).download_name(volume, ty,
                                                             'json')

    def pregenerate_zip_files(self, category):
        print "%d (json)" % category.id
        for volume in category.info.get('volumes', []):
            self._make_zip(volume, 'tagging')
            self._make_zip(volume, 'describing')
            self._make_zip(volume, 'commenting')
