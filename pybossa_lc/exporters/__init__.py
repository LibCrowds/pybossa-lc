# -*- coding: utf8 -*-
"""Volume exporter module for pybossa-lc."""

import json
import itertools
from flatten_json import flatten
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
        """Parse a result to get simple annotation values for a motivation."""
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

    def _get_data(self, motivation, volume_id, flat=False):
        """Get volume data for a given annotation motivation."""
        if not flat:
            return volumes_cache.get_annotations(volume_id, motivation)

        # Collate annotation data for each target
        target_data = {}
        tmpl_results = volumes_cache.get_tmpl_results(volume_id)
        for tmpl_id, data in tmpl_results.items():
            for result in data['results']:
                target = self._get_target(result)
                if target:
                    simple_data = self._get_simple_data(result, motivation)
                    task_id = result['task_id']
                    parent_task_id = result['info'].get('parent_task_id', None)
                    target_row = target_data.get(target, [])
                    target_row.append({
                        'task_id': task_id,
                        'parent_task_id': parent_task_id,
                        'template_id': tmpl_id,
                        'data': simple_data
                    })
                    target_data[target] = target_row

        templates = templates_cache.get_all()
        template_names = {tmpl['id']: tmpl['project']['name']
                          for tmpl in templates}

        # Merge annotations for each row
        merged_data = {}
        for target, anno_data in target_data.items():
            row = dict(target=target)
            for anno in anno_data:
                for tag, value in anno['data'].items():
                    if tag in row:
                        tag_row = row[tag]
                        if isinstance(tag_row, list):
                            tag_row.append(value)
                            row[tag] = tag_row
                        else:
                            row[tag] = [row[tag], value]
                    else:
                        row[tag] = value
            merged_data[target] = flatten(row)
        final_data = merged_data.values()

        # Ensure same keys exist in all rows
        keys_lists = [row.keys() for row in final_data]
        keys = list(set(itertools.chain(*keys_lists)))
        for row in final_data:
            for key in keys:
                row[key] = row.get(key, None)

        # Return sorted by target
        return sorted(final_data, key=lambda x: x['target'])
