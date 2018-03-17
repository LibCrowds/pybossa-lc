# -*- coding: utf8 -*-
"""IIIF importer module for pybossa-lc"""
import requests
from pybossa.importers.base import BulkTaskImport


class BulkTaskIIIFImporter(BulkTaskImport):
    """Class to import tasks from IIIF manifests."""

    importer_id = "iiif-annotation"

    def __init__(self, manifest_uri, parent_id=None):
        """Init method."""
        self.manifest_uri = manifest_uri
        self.parent_id = parent_id

    def tasks(self):
        """Get tasks."""
        return self._generate_tasks()

    def count_tasks(self):
        """Count number of tasks."""
        return len(self.tasks())

    def _generate_tasks(self):
        """Generate the tasks."""
        manifest = requests.get(self.manifest_uri).json()
        task_data = self._get_task_data(manifest)
        if self.parent_id:
            task_data = self._enhance_task_data(task_data, self.parent_id)
        return [dict(info=data) for data in task_data]

    def _get_task_data(self, manifest):
        """Return the task data generated from a manifest."""
        manifest_uri = manifest['@id']
        canvases = manifest['sequences'][0]['canvases']
        images = [c['images'][0]['resource']['service']['@id']
                  for c in canvases]

        data = []
        for i, img in enumerate(images):
            row = {
                'tileSource': '{}/info.json'.format(img),
                'target': canvases[i]['@id'],
                'manifest': manifest_uri,
                'thumbnailUrl': '{}/full/256,/0/default.jpg'.format(img),
                'shareUrl': self._get_share_url(manifest_uri, i)
            }
            data.append(row)
        return data

    def _enhance_task_data(self, task_data, parent_id):
        """Add tasks according to the results of a parent task."""
        from pybossa.core import result_repo
        indexed_task_data = {row['target']: row for row in task_data}
        enhanced_task_data = []
        results = result_repo.filter_by(project_id=parent_id)
        for result in results:
            if not result.info:
                raise ValueError('The info field for a result is empty')
            annotations = result.info['annotations']

            for anno in annotations:
                if anno['motivation'] == 'tagging':
                    source = anno['target']['source']
                    selector = anno['target']['selector']['value']
                    rect = selector.split('=')[1].split(',')
                    data = indexed_task_data[source].copy()
                    data['highlights'] = [
                        {
                            'x': float(rect[0]),
                            'y': float(rect[1]),
                            'width': float(rect[2]),
                            'height': float(rect[3])
                        }
                    ]
                    data['bounds'] = {
                        'x': float(rect[0]) + -200,
                        'y': float(rect[1]) + 0,
                        'width': float(rect[2]) + 400,
                        'height': float(rect[3]) + 0
                    }
                    data['parent_task_id'] = result.task_id
                    enhanced_task_data.append(data)

                elif anno['motivation'] != 'commenting':
                    raise ValueError('Unhandled motivation')

        # Sort by target and any highlights
        return sorted(enhanced_task_data,
                      key=lambda x: (
                          x['target'],
                          x['highlights'][0]['y'],
                          x['highlights'][0]['x']
                      ))

    def _get_share_url(self, manifest_uri, canvas_index):
        """Return a Universal Viewer URL for sharing."""
        base = 'http://universalviewer.io/uv.html'
        query = '#?cv={}'.format(canvas_index)

        # Use the BL viewer for BL items
        if '://api.bl.uk/metadata/iiif/' in manifest_uri:
            base = manifest_uri.replace(
                'api.bl.uk/metadata/iiif',
                'access.bl.uk/item/viewer'
            )
            base = base.replace('/manifest.json', '')
            base = base.replace('https://', 'http://')
        else:
            query = '?manifest={0}{1}'.format(manifest_uri, query)

        return base + query
