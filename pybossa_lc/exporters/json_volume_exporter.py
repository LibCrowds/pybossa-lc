# -*- coding: utf8 -*-
"""JSON volume exporter module for pybossa-lc."""

import json
import tempfile
from collections import namedtuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pybossa.exporter import Exporter
from pybossa.core import uploader


class JsonVolumeExporter(Exporter):

    def gen_json(self, table, project_id):
        pass

    def _respond_json(self, ty, volume_id):
        return self.gen_json(ty, volume_id)

    def _make_zip(self, volume_dict, ty):
        Volume = namedtuple('Volume', 'id name short_name category_id')
        volume = Volume(**volume_dict)
        name = self._project_name_latin_encoded(volume)
        json_task_generator = self._respond_json(ty, volume.id)
        if json_task_generator is not None:
            datafile = tempfile.NamedTemporaryFile()
            try:
                datafile.write(json.dumps(json_task_generator))
                datafile.flush()
                zipped_datafile = tempfile.NamedTemporaryFile()
                try:
                    _zip = self._zip_factory(zipped_datafile.name)
                    fn = '%s_%s.json' % (name, ty)
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

    def download_name(self, volume_dict, ty):
        Volume = namedtuple('Volume', 'name short_name')
        volume = Volume(**volume_dict)
        return super(JsonVolumeExporter, self).download_name(volume, ty,
                                                             'json')

    def pregenerate_zip_files(self, category):
        print "%d (json)" % category.id
        for volume in category.info.get('volumes', []):
            self._make_zip(volume, volume.name)
