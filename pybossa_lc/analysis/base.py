# -*- coding: utf8 -*-
"""Base analyst module for pybossa-lc.

Provides an abstract base class with methods common to each specific analyst
type.

One subclass should be provided for each type of task presenter.
"""

import six
import math
import json
import uuid
import numpy
import string
import pandas
import dateutil
import dateutil.parser
from datetime import datetime
from titlecase import titlecase
from flask import current_app, render_template
from rq import Queue
from abc import ABCMeta, abstractmethod
from pybossa.core import sentinel
from pybossa.jobs import send_mail

from . import AnalysisException


MAIL_QUEUE = Queue('email', connection=sentinel.master)


@six.add_metaclass(ABCMeta)
class BaseAnalyst():

    @abstractmethod
    def get_comments(self, task_run_df):  # pragma: no cover
        """Return a list of tuples with the format (user_id, comment)."""
        pass

    @abstractmethod
    def get_tags(self, task_run_df):  # pragma: no cover
        """Return a dict of tags against fragment selectors."""
        pass

    @abstractmethod
    def get_transcriptions_df(self, task_run_df):  # pragma: no cover
        """Return a dataframe of transcriptions."""
        pass

    def analyse(self, result_id, silent=True):
        """Analyse a result."""
        from pybossa.core import result_repo, task_repo
        result = result_repo.get(result_id)
        task = task_repo.get_task(result.task_id)
        task_runs = task_repo.filter_task_runs_by(task_id=task.id)

        # Check for modified results
        if result.info and result.info.get('modified'):
            return

        # Check for parent results
        if result.info and result.info.get('has_children'):
            return

        task_run_df = self.get_task_run_df(task_runs)
        tmpl = self.get_project_template(result.project_id)
        target = self.get_task_target(task)
        annotations = []
        is_complete = True

        # Handle comments
        comments = self.get_comments(task_run_df)
        for comment in comments:
            user_id = comment[0]
            value = comment[1]
            comment_anno = self.create_commenting_anno(target, value, user_id)
            annotations.append(comment_anno)
            if not silent:
                self.email_comment_anno(task, comment_anno)

        # Handle tags
        tags = self.get_tags(task_run_df)
        for tag, rects in tags.items():
            clusters = self.cluster_rects(rects)
            for cluster in clusters:
                fragment_target = self.create_fragment_target(target, cluster)
                tagging_anno = self.create_tagging_anno(fragment_target, tag)
                annotations.append(tagging_anno)

        # Get non-empty transcriptions
        df = self.get_transcriptions_df(task_run_df)
        df = self.drop_empty_rows(df)

        # Normalise Transcriptions
        norm_func = self.normalise_transcription
        df = df.applymap(lambda x: norm_func(x, tmpl.rules))

        # Store matching answers matching answers or update n_answers
        has_matches = self.has_n_matches(tmpl.min_answers, df)
        if has_matches:
            for column in df:
                value = df[column].value_counts().idxmax()
                anno = self.create_describing_anno(target, value, column)
                annotations.append(anno)
        elif not df.empty:
            is_complete = False

        self.update_n_answers_required(task, is_complete, tmpl.max_answers)

        # Apply rule to strip fragment selectors
        rule = 'remove_fragment_selector'
        if isinstance(tmpl.rules, dict) and tmpl.rules.get(rule):
            map(self.strip_fragment_selector, annotations)

        result.info = dict(annotations=annotations)
        result_repo.update(result)

    def analyse_all(self, project_id):
        """Analyse all results for a project."""
        from pybossa.core import result_repo
        results = result_repo.filter_by(project_id=project_id)
        for result in results:
            self.analyse(result.id)

    def analyse_empty(self, project_id):
        """Analyse all empty results for a project."""
        from pybossa.core import result_repo
        results = result_repo.filter_by(project_id=project_id)
        empty_results = [r for r in results if not r.info]
        for result in empty_results:
            self.analyse(result.id)

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

    def has_n_matches(self, min_answers, task_run_df):
        """Check if minimum matching answers for each key."""
        task_run_df = task_run_df.replace(numpy.nan, '')
        if task_run_df.empty:
            return False
        for k in task_run_df.keys():
            if task_run_df[k].value_counts().max() < min_answers:
                return False
        return True

    def get_task_run_df(self, task_runs):
        """Load task run info into a dataframe."""
        if not task_runs:
            msg = 'Task {} has no task runs!'.format(task_id)
            raise AnalysisException(msg)

        data = [self.explode_info(tr) for tr in task_runs]
        index = [tr.__dict__['id'] for tr in task_runs]
        return pandas.DataFrame(data, index)

    def explode_info(self, item):
        """Explode first level item info keys."""
        item_data = item.__dict__
        protected = item_data.keys()
        if type(item.info) == dict:
            for k, v in item_data['info'].items():
                if k in protected:
                    # Prefix if info key also exists as core task run key
                    item_data["_" + k] = v
                else:
                    item_data[k] = v
        return item_data

    def get_project_template(self, project_id):
        """Return the project's template."""
        from pybossa.core import project_repo
        from .. import project_tmpl_repo
        project = project_repo.get(project_id)
        template_id = project.info.get('template_id')
        if not template_id:
            msg = 'Invalid project template: Project {}'.format(project.id)
            raise ValueError(msg)

        tmpl = project_tmpl_repo.get(template_id)
        if not tmpl:  # pragma: no cover
            msg = 'Invalid project template: Project {}'.format(project.id)
            raise ValueError(msg)

        return tmpl

    def normalise_case(self, value, rules):
        """Normalise the case of a string."""
        if rules.get('case') == 'title':
            return titlecase(value.lower())
        elif rules.get('case') == 'lower':
            return value.lower()
        elif rules.get('case') == 'upper':
            return value.upper()
        return value

    def normalise_whitespace(self, value, rules):
        """Normalise the whitespace of a string."""
        if rules.get('whitespace') == 'normalise':
            return " ".join(value.split())
        elif rules.get('whitespace') == 'underscore':
            return " ".join(value.split()).replace(' ', '_')
        elif rules.get('whitespace') == 'full_stop':
            return " ".join(value.split()).replace(' ', '.')
        return value

    def normalise_dates(self, value, rules):
        """Normalise a date string."""
        if not rules.get('date_format'):
            return value

        # Trim trailing whitespace
        value = " ".join(value.split())

        # Strip punctuation
        value = value.strip(string.punctuation)

        # Ensure we have at least four digits
        if len(value) < 4:
            return ''

        dayfirst = rules.get('dayfirst', False)
        yearfirst = rules.get('yearfirst', False)
        try:
            ts = dateutil.parser.parse(value, dayfirst=dayfirst,
                                       yearfirst=yearfirst)
        except (ValueError, TypeError):
            return ''
        iso = ts.isoformat()[:10]

        # Strip the year if it was not given
        no_start_year = yearfirst and not value.startswith(str(ts.year))
        no_end_year = not yearfirst and not value.endswith(str(ts.year))
        if no_start_year or no_end_year:
            iso = iso[4:]

        return iso

    def normalise_punctuation(self, value, rules):
        """Normalise string punctuation."""
        if rules.get('trim_punctuation'):
            return value.strip(string.punctuation)
        return value

    def normalise_transcription(self, value, rules):
        """Normalise value according to the specified analysis rules."""
        if not rules or not isinstance(value, basestring):
            return value

        normalised = value
        normalised = self.normalise_case(normalised, rules)
        normalised = self.normalise_whitespace(normalised, rules)
        normalised = self.normalise_punctuation(normalised, rules)
        normalised = self.normalise_dates(normalised, rules)
        return normalised

    def update_n_answers_required(self, task, is_complete, max_answers=10):
        """Update number of answers required for a task."""
        from pybossa.core import task_repo
        task_runs = task_repo.filter_task_runs_by(task_id=task.id)
        n_task_runs = len(task_runs)
        if not is_complete and task.n_answers < max_answers:
            task.state = "ongoing"
            if n_task_runs >= task.n_answers:
                task.n_answers = task.n_answers + 1
        else:
            task.n_answers = len(task_runs)
            task.state = "completed"
        task_repo.update(task)

    def replace_df_keys(self, df, **kwargs):
        """Replace a set of keys in a dataframe."""
        if not kwargs:
            return df
        df = df.rename(columns=kwargs)

        def sjoin(x):
            return ';'.join(x[x.notnull()].astype(str))

        return df.groupby(level=0, axis=1).apply(lambda x: x.apply(sjoin,
                                                                   axis=1))

    def get_task_target(self, task):
        """Get the target for different types of task."""
        if 'target' in task.info:  # IIIF tasks
            return task.info['target']
        elif 'link' in task.info:  # Flickr tasks
            return task.info['link']

    def get_raw_image_from_target(self, task):
        """Get the raw image from a target."""
        if 'tileSource' in task.info:  # IIIF tasks
            target_base = task.info['tileSource'].rstrip('/info.json')
            return target_base + '/full/600,/0/default.jpg'
        elif 'link' in task.info:  # Flickr tasks
            return task.info['url']
        return None

    def get_xsd_datetime(self):
        """Return timestamp expressed in the UTC xsd:datetime format."""
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    def create_fragment_target(self, target, rect):
        """Return a fragment target."""
        return {
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'],
                                                        rect['w'], rect['h'])
            }
        }

    def get_anno_generator(self):
        """Return a reference to the LibCrowds software."""
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        github_repo = current_app.config.get('GITHUB_REPO')
        return {
            "id": github_repo,
            "type": "Software",
            "name": "LibCrowds",
            "homepage": spa_server_name
        }

    def get_anno_creator(self, user):
        """Return a reference to a LibCrowds user."""
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        url = '{}/api/user/{}'.format(spa_server_name.rstrip('/'), user.id)
        return {
            "id": url,
            "type": "Person",
            "name": user.fullname,
            "nickname": user.name
        }

    def get_anno_base(self, motivation):
        """Return the base for a new Web Annotation."""
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        anno_uuid = str(uuid.uuid4())
        _id = '{0}/lc/annotations/wa/{1}'.format(spa_server_name, anno_uuid)
        ts_now = self.get_xsd_datetime()
        return {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": _id,
            "type": "Annotation",
            "motivation": motivation,
            "created": ts_now,
            "generated": ts_now,
            "generator": self.get_anno_generator()
        }

    def create_commenting_anno(self, target, value, user_id=None):
        """Create a Web Annotation with the commenting motivation."""
        from pybossa.core import user_repo
        anno = self.get_anno_base('commenting')
        anno['target'] = target
        anno['body'] = {
            "type": "TextualBody",
            "value": value,
            "purpose": "commenting",
            "format": "text/plain"
        }

        if user_id:
            user = user_repo.get(user_id)
            if user:
                anno['creator'] = self.get_anno_creator(user)
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

    def cluster_rects(self, rects):
        """Return clustered rectangles."""
        clusters = []
        merge_ratio = 0.5

        for rect in rects:
            r1 = rect
            matched = False
            for i in range(len(clusters)):
                r2 = clusters[i]
                overlap_ratio = self.get_overlap_ratio(r1, r2)
                if overlap_ratio > merge_ratio:
                    matched = True
                    r3 = self.merge_rects(r1, r2)
                    clusters[i] = r3

            if not matched:
                clusters.append(rect)

        return clusters

    def email_comment_anno(self, task, anno):
        """Email a comment annotation to administrators."""
        should_send = current_app.config.get('EMAIL_COMMENT_ANNOTATIONS')
        if not should_send:  # pragma: no cover
            return

        admins = current_app.config.get('ADMINS')
        creator = anno.get('creator', {}).get('name', None)
        comment = anno['body']['value']
        raw_image = self.get_raw_image_from_target(task)
        link = task.info.get('link')
        json_anno = json.dumps(anno, indent=2, sort_keys=True)
        msg = dict(subject='New Comment Annotation', recipients=admins)
        msg['body'] = render_template('/account/email/new_comment_anno.md',
                                      creator=creator,
                                      comment=comment,
                                      raw_image=raw_image,
                                      link=link,
                                      annotation=json_anno)
        msg['html'] = render_template('/account/email/new_comment_anno.html',
                                      creator=creator,
                                      comment=comment,
                                      raw_image=raw_image,
                                      link=link,
                                      annotation=json_anno)
        MAIL_QUEUE.enqueue(send_mail, msg)

    def strip_fragment_selector(self, anno):
        """Strip a fragment selector from an annotation, if present."""
        if isinstance(anno['target'], dict) and 'source' in anno['target']:
            anno['target'] = anno['target']['source']
        return anno
