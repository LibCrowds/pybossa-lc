# -*- coding: utf8 -*-
"""IIIF importer module for pybossa-lc"""
import requests
from pybossa.importers.base import BulkTaskImport


class BulkTaskIIIFImporter(BulkTaskImport):
    """Class to import tasks from IIIF manifests."""

    importer_id = "iiif"

    def __init__(self, manifest_url, template):
        """Init method."""
        self.manifest_url = manifest_url
        self.template = template

    def tasks(self):
        """Get tasks."""
        return self._generate_tasks()

    def count_tasks(self):
        """Count number of tasks."""
        return len(self.tasks())

    def _generate_tasks(self):
        """Generate the tasks."""
        manifest = requests.get(self.manifest_url)
        tasks = self._get_task_data_from_manifest(manifest)
        return tasks

    def _get_task_data_from_manifest(self, manifest):
        """Return the task data generated from a manifest."""
        manifest_url = manifest['@id']
        canvases = manifest['sequences'][0]['canvases']
        images = [c['images'][0]['resource']['service']['@id']
                  for c in canvases]

        data = []
        for i, img in enumerate(images):
            row = {
                'tileSource': img + '/info.json',
                'target': canvases[i]['@id'],
                'info': manifest_url,
                'thumbnailUrl': img + '/full/256,/0/default.jpg',
                'shareUrl': self._get_share_url(manifest_url, i)
            }
            row['mode'] = self.template['mode']
            row['tag'] = self.template['tag']
            row['objective'] = self.template['objective']
            row['guidance'] = self.template['guidance']
            if self.template['fields']:
                row['form'] = {
                    'model': {},
                    'schema': {
                        'fields': self.template['fields']
                    }
                }
            data.append(row)
        return data

    def _get_share_url(self, manifest_url, canvas_index):
        """Return a Universal Viewer URL for sharing."""
        base = 'http://universalviewer.io/uv.html'
        query = '#?cv={}'.format(canvas_index)

        # Use the BL viewer for BL items
        if '://api.bl.uk/metadata/iiif' in base:
            base = base.replace(
                'api.bl.uk/metadata/iiif',
                'access.bl.uk/item/viewer'
            )
            base = base.replace('/manifest.json', '')
            base = base.replace('https://', 'http://')
            query = '?manifest={0}{1}'.format(manifest_url, query)

        return base + query
