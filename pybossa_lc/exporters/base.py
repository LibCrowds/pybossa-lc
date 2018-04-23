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
from ..cache import volumes as volumes_cache


session = db.slave_session


class CustomExporterBase(Exporter):

    def __init__(self):
        super(CustomExporterBase, self)

    def _container(self, category):
        """Overwrite the container method."""
        return "category_{}".format(category.id)

    def download_name(self, category, motivation, _format):
        """Overwrite the download name method."""
        cat_enc_name = self._project_name_latin_encoded(category)
        filename = '%s_%s_%s.zip' % (cat_enc_name, motivation, _format)
        filename = secure_filename(filename)
        return filename

    def _get_anno_data(self, result, motivation):
        """Parse a result to get simple annotation values for a motivation."""
        if 'annotations' not in result.info:
            return None

        data = {}
        annotations = [anno for anno in result.info['annotations']
                       if anno['motivation'] == motivation]
        for annotation in annotations:

            # Transcription data
            if motivation == 'describing':
                tag = [row['value'] for row in annotation['body']
                       if row['purpose'] == 'tagging'][0]
                value = [row['value'] for row in annotation['body']
                         if row['purpose'] == 'describing'][0]
                data[tag] = value

            # Tagging data
            elif motivation == 'tagging':
                tag = [row['value'] for row in annotation['body']
                       if row['purpose'] == 'tagging'][0]
                if isinstance(annotation['target'], dict):
                    value = annotation['target']['selector']['value']
                else:
                    value = None
                data[tag] = value

            # Comments data
            elif motivation == 'commenting':
                data['comment'] = annotation['body']['value']

        return data

    def _get_target(self, result):
        """Parse a result to get the Web Annotation target."""
        if not isinstance(result.info, dict):
            return None

        if not result.info.get('annotations'):
            return None

        target = None
        for annotation in result.info['annotations']:
            temp_target = None
            if isinstance(annotation['target'], basestring):
                temp_target = annotation['target']
            elif isinstance(annotation['target'], dict):
                temp_target = annotation['target']['source']
            else:
                raise ValueError('Annotation target not defined')

            if target and target != temp_target:
                raise ValueError('Annotations contain different targets')

            target = temp_target
        return target

    def _get_results_data(self, results, motivation):
        """Return a dictionary of results data mapped to target or task ID."""
        data = {}
        for result in results:
            target = self._get_target(result)

            if target:
                anno_data = self._get_anno_data(result, motivation)
                annotations = data.get(target, {})

                for key in anno_data:
                    values = annotations.get(key, [])
                    values.append(anno_data[key])
                    annotations[key] = values

                data[target] = annotations

        return data

    def _get_data(self, category, motivation, flat=True):
        """Get annotation data for custom export."""
        data = {}
        projects = project_repo.filter_by(category_id=category.id)
        project_ids = [project.id for project in projects]
        results = result_repo.filter_by(project_id=project_ids)
        data = self._get_results_data(results, motivation)

        if not flat:
            return data.values()

        flat_data = []
        for target in data:
            row = flatten(data[target])
            row['target'] = target
            flat_data.append(row)

        # Return sorted by target
        return sorted(flat_data, key=lambda x: x['target'])
