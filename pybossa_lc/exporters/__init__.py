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

from .. import project_tmpl_repo
from ..cache import volumes as volumes_cache


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

        tmpls = project_tmpl_repo.get_all()
        tmpl_names = {tmpl['id']: tmpl['name'] for tmpl in tmpls}

        data = {}
        tmpl_results = volumes_cache.get_tmpl_results(volume_id)
        for tmpl_id, results in tmpl_results.items():
            tmpl_name = tmpl_names[tmpl_id]
            for result in results:
                target = self._get_target(result)
                if target:
                    simple_data = self._get_simple_data(result, motivation)
                    target_data = data.get(target, {})
                    tmpl_data = target_data.get(tmpl_name, {})
                    for key in simple_data:
                        values = tmpl_data.get(key, [])
                        values.append(simple_data[key])
                        tmpl_data[key] = values
                    target_data[tmpl_name] = tmpl_data

                    # Add share URLs
                    share_urls = target_data.get('share_url', [])
                    share_urls.append(result['share_url'])
                    target_data['share_url'] = list(set(share_urls))

                    # Add task state
                    current_state = result.get('task_state')
                    if current_state != 'ongoing':
                        target_data['task_state'] = result['task_state']

                    data[target] = target_data

        flat_data = []
        for target in data:
            row = dict(target=target)
            row.update(flatten(data[target]))
            flat_data.append(row)

        # Return sorted by target
        return sorted(flat_data, key=lambda x: x['target'])
