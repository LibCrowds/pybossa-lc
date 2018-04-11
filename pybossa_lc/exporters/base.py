# -*- coding: utf8 -*-
"""Volume exporter base module for pybossa-lc."""

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


class CustomExporterBase(Exporter):

    def __init__(self):
        super(CustomExporterBase, self)

    def _container(self, volume):
        return "category_{}".format(volume.category_id)

    def download_name(self, category, export_fmt, _format):
        """Overwrite the download name method."""
        enc_name = self._project_name_latin_encoded(title)
        filename = '%s_%s_%s.zip' % (enc_name, motivation, _format)
        filename = secure_filename(filename)
        return filename

    def _get_anno_data(self, result, motivation):
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

    def _get_export_format(self, category, export_fmt_id):
        """Get the export format."""
        export_formats = category.info.get('export_formats', [])
        return [fmt for fmt in export_formats if fmt['id'] == export_fmt_id][0]

    def _get_template(self, category, template_id):
        """Get the export format."""
        templates = category.info.get('templates', [])
        return [tmpl for tmpl in templates if tmpl['id'] == template_id][0]

    def _get_results_data(self, results, split_by_task_id=False):
        """Return a dictionary of results data mapped to target or task ID."""
        data = {}
        for result in results:
            target = self._get_target(result)
            if target:
                anno_data = self._get_anno_data(result, motivation)
                target_data = data.get(target, {})
                tmpl_data = target_data.get(tmpl_name, {})
                for key in anno_data:
                    values = tmpl_data.get(key, [])
                    values.append(anno_data[key])
                    tmpl_data[key] = values
                target_data[tmpl_name] = tmpl_data

                # Add share links
                links = target_data.get('link', [])
                links.append(result['link'])
                target_data['link'] = list(set(links))

                # Add task state
                current_state = result.get('task_state')
                if current_state != 'ongoing':
                    target_data['task_state'] = result['task_state']

                data[target] = target_data

    def _get_data(self, category, export_fmt_id, flat=True):
        """Get annotation data for custom export."""
        export_format = self._get_export_format(category, export_fmt_id)
        if not flat:
            # TODO: return unflattened annotations
            return []

        # Get root template
        root_tmpl_id = export_format.get('root_template_id')
        root_template = None
        if root_tmpl_id:
            root_template = self._get_template(category, root_tmpl_id)

        # Get included templates
        include_ids = export_format.get('include')
        include = None
        if include_ids:
            include = [self._get_template(category, tmpl_id)
                       for tmpl_id in include_ids]

        data = {}

        flat_data = []
        for target in data:
            row = dict(target=target)
            row.update(flatten(data[target]))
            flat_data.append(row)

        # Return sorted by target
        return sorted(flat_data, key=lambda x: x['target'])
