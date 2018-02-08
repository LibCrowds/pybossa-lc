# -*- coding: utf8 -*-
"""Volume exporter module for pybossa-lc."""

import json
from pybossa.core import db
from sqlalchemy import text
from pybossa.exporter import Exporter
from pybossa.core import project_repo
from werkzeug.utils import secure_filename
from sqlalchemy.orm.base import _entity_descriptor
from pybossa.model.result import Result

from ..cache import volumes as volumes_cache
from ..cache import exports as exports_cache
from ..cache import templates as templates_cache


session = db.slave_session


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

    def _get_data(self, export_fmt_id, volume_id):
        """Get the volume data according to the custom export format."""
        # results = volumes_cache.get_results_by_volume(volume_id)
        export_format = exports_cache.get_by_id(export_fmt_id)
        fields = export_format.get('fields', [])
        tmpl_ids = [field['template_id'] for field in fields
                    if field.get('template_id')]
        tmpl_results = exports_cache.get_results_by_tmpl_and_volume(tmpl_ids,
                                                                    volume_id)
        data = []
        print tmpl_results


        return [dict(test=123)]
