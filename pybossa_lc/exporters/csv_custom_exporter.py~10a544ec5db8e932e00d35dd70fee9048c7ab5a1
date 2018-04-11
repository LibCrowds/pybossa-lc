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

    def _respond_csv(self, category, root_template_id, include, motivation):
        export_data = self._get_data(category, root_template_id, include,
                                     motivation, flat=True)
        return pandas.DataFrame(export_data)

    def _make_zip(self, category, title, root_template_id, include,
                  motivation):
        name = self._project_name_latin_encoded(title)
        dataframe = self._respond_csv(category, root_template_id, include,
                                      motivation)
        if dataframe is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                dataframe.to_csv(datafile, index=False,
                                 encoding='utf-8')
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.csv' % (name, motivation)
                    _zip.write(datafile.name, secure_filename(fn))
                    _zip.close()
                    container = "category_%d" % category.id
                    dl_fn = self.download_name(title, motivation)
                    _file = FileStorage(filename=dl_fn, stream=zipped_datafile)
                    uploader.upload_file(_file, container=container)
                finally:
                    zipped_datafile.close()
            finally:
                datafile.close()

    def download_name(self, volume, ty):
        return super(CsvCustomExporter, self).download_name(volume, ty, 'csv')

    def pregenerate_zip_files(self, category):
        print "%d (csv)" % category.id
        for export_format in category.info.get('export_formats', []):
            self._make_zip(category,
                           export_format['title'],
                           export_format['root_template_id'],
                           export_format['include'],
                           export_format['motivation'])
