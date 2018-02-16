# -*- coding: utf8 -*-
"""Analysis module for pybossa-lc."""

import math
import numpy
import string
import pandas
import dateutil
import dateutil.parser
from datetime import datetime
from titlecase import titlecase
from flask import current_app
from pybossa.jobs import project_export
from pybossa.core import task_repo, project_repo, result_repo

from ..cache import templates as templates_cache


class Analyst(object):

    def __init__(self, project_id):
        self.project = project_repo.get(project_id)

    def analyse(self, result_id):
        raise NotImplementedError("Must override analyse")

    def analyse_all(self, analysis_func):
        """Analyse all results for a project."""
        results = result_repo.filter_by(project_id=self.project.id)
        for result in results:
            self.analyse(result.id)
        if results:
            project_export(self.project.id)

    def analyse_empty(self, analysis_func):
        """Analyse all empty results for a project."""
        results = result_repo.filter_by(project_id=self.project.id)
        empty_results = [r for r in results if not r.info]
        for result in empty_results:
            self.analyse(result.id)
        if empty_results:
            project_export(self.project.id)

    def drop_keys(self, task_run_df, keys):
        """Drop keys from the info fields of a task run dataframe."""
        keyset = set()
        for i in range(len(task_run_df)):
            for k in task_run_df.iloc[i].keys():
                keyset.add(k)
        keys = [k for k in keyset if k not in keys]
        return task_run_df[keys]

    def drop_empty_rows(self, task_run_df):
        """Drop rows that contain no data."""
        task_run_df = task_run_df.replace('', numpy.nan)
        task_run_df = task_run_df.dropna(how='all')
        return task_run_df

    def has_n_matches(self, task_run_df, n_task_runs, match_percentage):
        """Check if n percent of answers match for each key."""
        required = int(math.ceil(n_task_runs * (match_percentage / 100.0)))

        # Replace NaN with the empty string
        task_run_df = task_run_df.replace(numpy.nan, '')

        for k in task_run_df.keys():
            if task_run_df[k].value_counts().max() < required:
                return False
        return True

    def get_task_run_df(self, task_id):
        """Load an Array of task runs into a dataframe."""
        task_runs = task_repo.filter_task_runs_by(task_id=task_id)
        data = [self.explode_info(tr) for tr in task_runs]
        index = [tr.__dict__['id'] for tr in task_runs]
        return pandas.DataFrame(data, index)

    def explode_info(self, item):
        """Explode first level item info keys."""
        item_data = item.__dict__
        protected = item_data.keys()
        if type(item.info) == dict:
            keys = item_data['info'].keys()
            for k in keys:
                if k in protected:
                    item_data["_" + k] = item_data['info'][k]
                else:
                    item_data[k] = item_data['info'][k]
        return item_data

    def get_project_template(self):
        """Return the project's template."""
        template_id = self.project.info.get('template_id')
        if not template_id:
            raise ValueError('Invalid project template')

        tmpl = templates_cache.get_by_id(template_id)
        if not tmpl:  # pragma: no-cover
            raise ValueError('Invalid project template')

        return tmpl

    def normalise_transcription(self, value, rules):
        """Normalise value according to the specified analysis rules."""
        if not rules or not isinstance(value, basestring):
            return value

        normalised = value

        # Normalise case
        if rules.get('case') == 'title':
            normalised = titlecase(normalised.lower())
        elif rules.get('case') == 'lower':
            normalised = normalised.lower()
        elif rules.get('case') == 'upper':
            normalised = normalised.upper()

        # Normalise whitespace
        if rules.get('whitespace') == 'normalise':
            normalised = " ".join(normalised.split())
        elif rules.get('whitespace') == 'underscore':
            normalised = " ".join(normalised.split()).replace(' ', '_')
        elif rules.get('whitespace') == 'full_stop':
            normalised = " ".join(normalised.split()).replace(' ', '.')

        # Normalise dates
        if rules.get('date_format'):
            dayfirst = rules.get('dayfirst', False)
            yearfirst = rules.get('yearfirst', False)
            try:
                ts = dateutil.parser.parse(normalised, dayfirst=dayfirst,
                                          yearfirst=yearfirst)
            except (ValueError, TypeError):
                return ''
            normalised = ts.isoformat()[:10]

        # Normalise punctuation
        if rules.get('trim_punctuation'):
            normalised = normalised.strip(string.punctuation)
        return normalised

    def update_n_answers_required(self, task, max_answers=10):
        """Update number of answers required for a task."""
        task_runs = task_repo.filter_task_runs_by(task_id=task.id)
        n_task_runs = len(task_runs)
        if task.n_answers < max_answers:
            task.state = "ongoing"
            if n_task_runs >= task.n_answers:
                task.n_answers = task.n_answers + 1
        else:
            task.state = "completed"
        task_repo.update(task)

    def replace_df_keys(self, df, **kwargs):
        """Replace a set of keys in a dataframe."""
        if not kwargs:
            return df
        df = df.rename(columns=kwargs)

        def sjoin(x):
            return ';'.join(x[x.notnull()].astype(str))

        return df.groupby(level=0, axis=1).apply(lambda x: x.apply(sjoin, axis=1))

    def get_task_target(self, task_id):
        """Get the target for different types of task."""
        task = task_repo.get_task(task_id)
        if 'target' in task.info:  # IIF Annotation tasks
            return task.info['target']
        elif 'link' in task.info:  # Flickr tasks
            return task.info['link']

    def get_xsd_datetime(self):
        """Return timestamp expressed in the UTC xsd:datetime format."""
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    def get_anno_generator(self):
        """Return a reference to the LibCrowds software."""
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        return {
            "id": spa_server_name,
            "type": "Software",
            "name": "LibCrowds",
            "homepage": spa_server_name
        }

    def get_anno_base(self, motivation):
        """Return the base fo ra new Web Annotation."""
        ts_now = self.get_xsd_datetime()
        return {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "type": "Annotation",
            "motivation": motivation,
            "created": ts_now,
            "generated": ts_now,
            "generator": self.get_anno_generator(),
            "modified": ts_now
        }

    def create_commenting_anno(self, target, value):
        """Create a Web Annotation with the commenting motivation."""
        anno = self.get_anno_base('commenting')
        anno['target'] = target
        anno['body'] = {
            "type": "TextualBody",
            "value": value,
            "purpose": "commenting",
            "format": "text/plain"
        }
        return anno

    def create_tagging_anno(self, target, value):
        """Create a Web Annotation with the tagging motivation."""
        anno = self.get_anno_base('tagging')
        anno['target'] = target
        anno['body'] = {
            "type": "TextualBody",
            "purpose": "tagging",
            "value": value
        }
        return anno

    def create_describing_anno(self, target, value, tag, modified=False):
        """Create a Web Annotation with the describing motivation."""
        anno = self.get_anno_base('describing')
        anno['target'] = target
        anno['body'] = [
            {
                "type": "TextualBody",
                "purpose": "describing",
                "value": value,
                "format": "text/plain"
            },
            {
                "type": "TextualBody",
                "purpose": "tagging",
                "value": tag
            }
        ]
        if modified:
            anno['body'][0]['modified'] = self.get_xsd_datetime()
        return anno

    def get_modified_annos(self, anno_list, tag):
        """Check for a manually modified describing annotation."""
        matches = []
        for anno in anno_list:
            if anno['motivation'] != 'describing':
                continue

            tag_matches = [body for body in anno['body']
                          if body['purpose'] == 'tagging' and
                          body['value'] == tag]
            modified = [body for body in anno['body']
                        if body['purpose'] == 'describing' and
                        'modified' in body]
            if tag_matches and modified:
                matches.append(anno)
        return matches

    def get_rect_from_selection_anno(self, anno):
        """Return a rectangle from a selection annotation."""
        media_frag = anno['target']['selector']['value']
        regions = media_frag.split('=')[1].split(',')
        return {
            'x': int(round(float(regions[0]))),
            'y': int(round(float(regions[1]))),
            'w': int(round(float(regions[2]))),
            'h': int(round(float(regions[3])))
        }

    def get_overlap_ratio(self, r1, r2):
        """Return the overlap ratio of two rectangles."""
        r1x2 = r1['x'] + r1['w']
        r2x2 = r2['x'] + r2['w']
        r1y2 = r1['y'] + r1['h']
        r2y2 = r2['y'] + r2['h']

        x_overlap = max(0, min(r1x2, r2x2) - max(r1['x'], r2['x']))
        y_overlap = max(0, min(r1y2, r2y2) - max(r1['y'], r2['y']))
        intersection = x_overlap * y_overlap

        r1_area = r1['w'] * r1['h']
        r2_area = r2['w'] * r2['h']
        union = r1_area + r2_area - intersection

        if not union:
            return 0

        overlap = float(intersection) / float(union)
        return overlap

    def merge_rects(self, r1, r2):
        """Merge two rectangles."""
        return {
            'x': min(r1['x'], r2['x']),
            'y': min(r1['y'], r2['y']),
            'w': max(r1['x'] + r1['w'], r2['x'] + r2['w']) - r2['x'],
            'h': max(r1['y'] + r1['h'], r2['y'] + r2['h']) - r2['y']
        }

    def update_selector(self, anno, rect):
        """Update a media frag selector."""
        frag = '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'], rect['w'],
                                              rect['h'])
        anno['target']['selector']['value'] = frag
        anno['modified'] = self.get_xsd_datetime()

    def cluster_tagging_annotations(self, anno_list):
        """Return clustered tagging annotations."""
        clusters = []
        merge_ratio = 0.5
        tagging_annos = [anno for anno in anno_list
                        if anno['motivation'] == 'tagging']

        for anno in tagging_annos:
            r1 = self.get_rect_from_selection_anno(anno)
            matched = False
            for cluster in clusters:
                r2 = self.get_rect_from_selection_anno(cluster)
                overlap_ratio = self.get_overlap_ratio(r1, r2)
                if overlap_ratio > merge_ratio:
                    matched = True
                    r3 = self.merge_rects(r1, r2)
                    self.update_selector(cluster, r3)

            if not matched:
                # still update to round rect params
                self.update_selector(anno, r1)
                clusters.append(anno)

        return clusters
