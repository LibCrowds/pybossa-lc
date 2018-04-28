# -*- coding: utf8 -*-
"""Volume exporter base module for pybossa-lc."""

import json
import itertools
from flatten_json import flatten
from pybossa.core import db
from sqlalchemy import text
from pybossa.exporter import Exporter
from pybossa.core import project_repo, result_repo
from werkzeug.utils import secure_filename
from sqlalchemy.orm.base import _entity_descriptor
from pybossa.model.result import Result

from .. import project_tmpl_repo
from ..cache import annotations as annotations_cache
from ..cache import volumes as volumes_cache


session = db.slave_session


class AnnotationExporterBase(Exporter):

    def __init__(self):
        super(AnnotationExporterBase, self)

    def _container(self, category):
        """Overwrite the container method."""
        return "category_{}".format(category.id)

    def download_name(self, category, motivation, _format):
        """Overwrite the download name method."""
        cat_enc_name = self._project_name_latin_encoded(category)
        filename = '%s_%s_%s.zip' % (cat_enc_name, motivation, _format)
        filename = secure_filename(filename)
        return filename

    def _get_data(self, category, motivation, flat=False):
        """Get annotation data for custom export."""
        contains = {'motivation': motivation}
        data = annotations_cache.search_by_category(category.id,
                                                    contains=contains)
        annotations = data['annotations']

        if flat:
            flat_data = []
            for anno in annotations:
                flat_anno = flatten(anno)
                flat_data.append(flat_anno)
            return flat_data

        return annotations
