# -*- coding: utf8 -*-
"""CSV volume exporter module for pybossa-lc."""

import json
import tempfile
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.core import uploader
import pandas

from .base import AnnotationExporterBase


class CsvAnnotationExporter(AnnotationExporterBase):

    def _respond_csv(self, category, motivation):
        export_data = self._get_data(category, motivation, flat=True)
        return pandas.DataFrame(export_data)

    def _make_zip(self, category, motivation):
        name = self._project_name_latin_encoded(category)
        dataframe = self._respond_csv(category, motivation)
        if dataframe is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                dataframe.to_csv(datafile, index=False, encoding='utf-8')
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.csv' % (name, motivation)
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
        return super(CsvAnnotationExporter, self).download_name(category,
                                                                motivation,
                                                                'csv')

    def pregenerate_zip_files(self, category):
        print "%d (csv)" % category.id
        for motivation in ['describing', 'tagging', 'commenting']:
            self._make_zip(category, motivation)
