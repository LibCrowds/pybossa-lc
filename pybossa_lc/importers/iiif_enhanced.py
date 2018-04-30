# -*- coding: utf8 -*-
"""Enhanced IIIF importer module for pybossa-lc"""

from pybossa.importers import BulkImportException
from pybossa.importers.iiif import BulkTaskIIIFImporter


class BulkTaskIIIFEnhancedImporter(BulkTaskIIIFImporter):
    """Import tasks from IIIF manifests with parent-child relationships."""

    importer_id = "iiif-enhanced"

    def __init__(self, manifest_uri, parent_id=None):
        """Init method."""
        super(BulkTaskIIIFEnhancedImporter, self).__init__(manifest_uri)
        self.parent_id = parent_id

    def _generate_tasks(self):
        """Generate the tasks."""
        task_data = super(BulkTaskIIIFEnhancedImporter, self)._generate_tasks()
        if not self.parent_id:
            return task_data

        child_task_data = self._get_child_task_data(task_data, self.parent_id)
        return [dict(info=data) for data in child_task_data]

    def _get_child_task_data(self, task_data, parent_id):
        """Generate tasks according to the results of a parent project."""
        from pybossa.core import result_repo
        indexed_task_data = {row['info']['target']: row['info']
                             for row in task_data}

        child_task_data = []
        results = result_repo.filter_by(project_id=parent_id)
        for result in results:
            # Check that parent result is valid
            err_msg = 'A result from the parent project has not been analysed'
            if not isinstance(result.info, dict):
                print 'foo'
                raise BulkImportException(err_msg)
            elif 'annotations' not in result.info:
                raise BulkImportException(err_msg)

            parent_annotations = [anno for anno in result.info['annotations']
                                  if anno['motivation'] != 'commenting']

            # Update related task for each parent annotation
            for anno in parent_annotations:
                source = anno['target']
                if isinstance(anno['target'], dict):
                    source = anno['target']['source']

                data = indexed_task_data.get(source)
                if not data:
                    err_msg = 'A parent annotation has an invalid target'
                    raise BulkImportException(err_msg)
                data_copy = data.copy()

                data_copy['target'] = anno['target']
                data_copy['parent_task_id'] = result.task_id
                data_copy['parent_annotation_id'] = anno['id']
                child_task_data.append(data_copy)

            # Add has_children key to parent result
            new_result_info = result.info.copy()
            new_result_info['has_children'] = True
            result.info = new_result_info
            result_repo.update(result)

        # Return sorted by target
        return sorted(child_task_data, key=lambda x: x['target'])

    def _get_link(self, manifest_uri, canvas_index):
        """Overwrite to return BL viewer link for BL items."""
        base = 'http://universalviewer.io/uv.html'
        query = '#?cv={}'.format(canvas_index)

        # Use the British Library viewer for British Library items
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
