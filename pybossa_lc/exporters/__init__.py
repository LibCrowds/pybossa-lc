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

    def _get_simple_data(self, result, motivation):
        """Parse a result to get the annotation values for a motivation."""
        if 'annotations' not in result['info']:
            return None

        data = {}
        annotations = [anno for anno in result['info']['annotations']
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

    def _get_full_data(self, result, motivation):
        """Parse a result to get the full annotations for a motivation."""
        if 'annotations' not in result['info']:
            return None

        return [anno for anno in result['info']['annotations']
                if anno['motivation'] == motivation]

    def _get_target(self, result):
        """Parse a result to get the Web Annotation target."""
        if 'annotations' not in result['info']:
            return None

        target = None
        for annotation in result['info']['annotations']:
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


    def _get_data(self, motivation, volume_id):
        """Get volume data for a task presenter type."""
        final_data = {}
        tmpl_results = volumes_cache.get_results(volume_id)
        for tmpl_id, data in tmpl_results.items():
            tmpl_data = []
            for result in data['results']:
                target = self._get_target(result)
                simple_data = self._get_simple_data(result, motivation)
                full_data = self._get_full_data(result, motivation)
                task_id = result['task_id']
                parent_task_id = result['info'].get('parent_task_id', None)
                tmpl_data.append({
                    'task_id': task_id,
                    'parent_task_id': parent_task_id,
                    'target': target,
                    'simple_data': simple_data,
                    'full_data': full_data
                })
            final_data[tmpl_id] = tmpl_data
        return final_data
