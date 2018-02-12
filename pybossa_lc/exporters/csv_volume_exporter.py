# -*- coding: utf8 -*-
"""CSV volume exporter module for pybossa-lc."""

import json
import tempfile
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.core import uploader
import pandas

from . import VolumeExporter


class CsvVolumeExporter(VolumeExporter):

    def _respond_csv(self, motivation, volume_id):
        export_data = self._get_data(motivation, volume_id)
        return pandas.DataFrame(export_data)

    def _make_zip(self, volume, ty):
        name = self._project_name_latin_encoded(volume)
        dataframe = self._respond_csv(ty, volume.id)
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
        return super(CsvVolumeExporter, self).download_name(volume, ty, 'csv')

    def pregenerate_zip_files(self, category):
        print "%d (csv)" % category.id
        for volume in category.info.get('volumes', []):
            self._make_zip(volume, volume.name)
