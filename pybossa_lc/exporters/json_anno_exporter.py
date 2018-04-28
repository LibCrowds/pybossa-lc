# -*- coding: utf8 -*-
"""JSON volume exporter module for pybossa-lc."""

import json
import tempfile
from collections import namedtuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.core import uploader

from .base import AnnotationExporterBase


class JsonAnnotationExporter(AnnotationExporterBase):

    def _respond_json(self, category, motivation):
        return self._get_data(category, motivation)

    def _make_zip(self, category, motivation):
        name = self._project_name_latin_encoded(category)
        json_data_generator = self._respond_json(category, motivation)
        if json_data_generator is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                datafile.write(json.dumps(json_data_generator))
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.json' % (name, motivation)
                    _zip.write(datafile.name, secure_filename(fn))
                    _zip.close()
                    container = self._container(category)
                    dl_fn = self.download_name(category, motivation)
                    _file = FileStorage(filename=dl_fn, stream=zipped_datafile)
                    uploader.upload_file(_file, container=container)
                finally:
                    zipped_datafile.close()
            finally:
                datafile.close()

    def download_name(self, category, motivation):
        return super(JsonAnnotationExporter, self).download_name(category,
                                                                 motivation,
                                                                 'json')

    def pregenerate_zip_files(self, category):
        print "%d (json)" % category.id
        for motivation in ['describing', 'tagging', 'commenting']:
            self._make_zip(category, motivation)
