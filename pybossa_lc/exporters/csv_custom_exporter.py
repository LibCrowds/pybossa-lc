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

    def _respond_csv(self, volume_id, motivation):
        export_data = self._get_data(motivation, volume_id, flat=True)
        return pandas.DataFrame(export_data)

    def _make_zip(self, volume, ty):
        name = self._project_name_latin_encoded(volume)
        dataframe = self._respond_csv(volume.id, ty)
        if dataframe is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                dataframe.to_csv(datafile, index=False,
                                 encoding='utf-8')
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.csv' % (name, ty)
                    _zip.write(datafile.name, secure_filename(fn))
                    _zip.close()
                    container = "category_%d" % volume.category_id
                    dl_fn = self.download_name(volume, ty)
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
        for volume in category.info.get('volumes', []):
            self._make_zip(volume, 'tagging')
            self._make_zip(volume, 'describing')
            self._make_zip(volume, 'commenting')
