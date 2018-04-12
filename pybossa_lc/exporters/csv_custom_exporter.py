# -*- coding: utf8 -*-
"""CSV volume exporter module for pybossa-lc."""

import json
import tempfile
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.core import uploader
import pandas

from .base import CustomExporterBase


class CsvCustomExporter(CustomExporterBase):

    def _respond_csv(self, category, export_fmt_id):
        export_data = self._get_data(category, export_fmt_id, flat=True)
        return pandas.DataFrame(export_data)

    def _make_zip(self, category, export_fmt_id):
        name = self._project_name_latin_encoded(category)
        dataframe = self._respond_csv(category, export_fmt_id)
        if dataframe is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                dataframe.to_csv(datafile, index=False, encoding='utf-8')
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.csv' % (name, export_fmt_id)
                    _zip.write(datafile.name, secure_filename(fn))
                    _zip.close()
                    container = self._container(category)
                    dl_fn = self.download_name(category, export_fmt_id)
                    _file = FileStorage(filename=dl_fn, stream=zipped_datafile)
                    uploader.upload_file(_file, container=container)
                finally:
                    zipped_datafile.close()
            finally:
                datafile.close()

    def download_name(self, category, export_fmt_id):
        return super(CsvCustomExporter, self).download_name(category,
                                                            export_fmt_id,
                                                            'csv')

    def pregenerate_zip_files(self, category):
        print "%d (csv)" % category.id
        for export_fmt in category.info.get('export_formats', []):
            self._make_zip(category, export_fmt['id'])
