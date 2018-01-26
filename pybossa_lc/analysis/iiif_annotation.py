# -*- coding: utf8 -*-
"""IIIF Annotation analysis module."""

import string
import datetime
import itertools
from pybossa.core import sentinel
from pybossa.jobs import send_mail
from rq import Queue

from . import helpers


MAIL_QUEUE = Queue('email', connection=sentinel.master)
MERGE_RATIO = 0.5


def get_overlap_ratio(r1, r2):
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

    overlap = float(intersection) / float(union)
    return overlap


def get_rect_from_selection(anno):
    """Return a rectangle from a selection annotation."""
    media_frag = anno['target']['selector']['value']
    regions = media_frag.split('=')[1].split(',')
    return {
        'x': int(round(float(regions[0]))),
        'y': int(round(float(regions[1]))),
        'w': int(round(float(regions[2]))),
        'h': int(round(float(regions[3])))
    }


def merge_rects(r1, r2):
    """Merge two rectangles."""
    return {
        'x': min(r1['x'], r2['x']),
        'y': min(r1['y'], r2['y']),
        'w': max(r1['x'] + r1['w'], r2['x'] + r2['w']) - r2['x'],
        'h': max(r1['y'] + r1['h'], r2['y'] + r2['h']) - r2['y']
    }


def get_transcribed_fields(anno):
    """Return all transcribed fields from the body of an annotation."""
    fields = {}
    body = anno.get('body')

    def add_field(body):
        key = None
        value = None
        for item in body:
            if item['purpose'] == 'tagging':  # the tag
                key = item['value']
            elif item['purpose'] == 'describing':  # the transcribed value
                value = item['value']
        fields[key] = value

    for item in body:
        if isinstance(item, list):  # multiple fields
            add_field(item)
        else:  # single field
            add_field(body)

    return fields


def merge_transcriptions(annos, rules):
    """Get the most common normalised transcriptions for each field.

    Normalises transcribed values then creates a dictionary with the following
    structure:

    {
      tag: {
          value1: {
              "annotation": { .. },
              "count": n
          },
          value2: {
              "annotation": { ... },
              "count": n
          }
      },
      tag: {
        ...
      }
    }

    Then returns the most commonly occuring annotations for each tag like so:

    {
      tag: {
          "annotation": { .. },
          "count": n
      },
      tag: {
        ...
      }
    }

    """
    data = {}
    for anno in annos:
        tag = None
        value = None
        for item in anno['body']:
            if item['purpose'] == 'tagging':  # the field tag
                tag = item['value']
            elif item['purpose'] == 'describing':  # the transcribed value
                value = normalise_transcription(item['value'], rules)
                item['value'] = value

        count = data.get(tag, {}).get(value, {}).get('count', 0) + 1
        if tag not in data:
            data[tag] = {}
        data[tag][value] = dict(annotation=anno, count=count)
        anno['modified'] = datetime.datetime.now().isoformat()

    reduced = {}
    for tag in data:
        for value in data[tag]:
            reduced[tag] = reduced.get(tag, {})
            n = data[tag][value]['count']
            if 'count' not in reduced[tag] or reduced[tag] < n:
                reduced[tag] = data[tag][value]

    return reduced


def normalise_transcription(value, rules):
    """Normalise transcriptions according to the specified analysis rules."""
    if not rules:
        return value

    normalised = value
    if rules.get('titlecase'):
        normalised = normalised.title()

    if rules.get('whitespace'):
        normalised = " ".join(normalised.split())

    if rules.get('trim_punctuation'):
        normalised = normalised.translate(None, string.punctuation)
    return normalised


def set_target_from_selection_parent(annotation, task):
    """Set the annotation target according to a selection parent task."""
    highlights = task.info.get('highlights')
    if not highlights:
        raise ValueError('This task was not built from a selection parent')

    rect = highlights[0]
    selector = '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'],
                                              rect['width'], rect['height'])
    annotation['target'] = {
        'source': annotation['target'],
        'selector': {
            'conformsTo': 'http://www.w3.org/TR/media-frags/',
            'type': 'FragmentSelector',
            'value': selector
        }
    }


def update_selector(anno, rect):
    """Update a media frag selector."""
    frag = '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'], rect['w'],
                                          rect['h'])
    anno['target']['selector']['value'] = frag
    anno['modified'] = datetime.datetime.now().isoformat()


def analyse(result_id):
    """Analyse a IIIF Annotation result."""
    from ..cache import results as results_cache
    from pybossa.core import result_repo, task_repo
    result = result_repo.get(result_id)
    task = task_repo.get_task(result.task_id)
    df = helpers.get_task_run_df(result.task_id)

    # Flatten all annotations for the task into a single list
    anno_list = df['info'].tolist()
    anno_list = list(itertools.chain.from_iterable(anno_list))

    result.info = dict(annotations=[])
    clusters = []
    comments = []
    transcriptions = []

    for anno in anno_list:
        if anno['motivation'] == 'commenting':
            comments.append(anno)
            continue

        # Cluster selected regions
        elif anno['motivation'] == 'tagging':
            r1 = get_rect_from_selection(anno)
            matched = False
            for cluster in clusters:
                r2 = get_rect_from_selection(cluster)
                overlap_ratio = get_overlap_ratio(r1, r2)
                if overlap_ratio > MERGE_RATIO:
                    matched = True
                    r3 = merge_rects(r1, r2)
                    update_selector(cluster, r3)

            if not matched:
                update_selector(anno, r1)  # still update to round rect params
                clusters.append(anno)

        # Add transcriptions to separate list
        elif anno['motivation'] == 'describing':
            transcriptions.append(anno)

        else:  # pragma: no cover
            raise ValueError('Unhandled motivation')

    result.last_version = True

    # Process transcriptions
    final_transcriptions = []
    if transcriptions:
        rules = helpers.get_analysis_rules(result.project_id)

        merged_transcriptions = merge_transcriptions(transcriptions, rules)
        for tag in merged_transcriptions:
            item = merged_transcriptions[tag]

            # Set annotation target from a selection parent
            if rules and rules.get('target_from_select_parent'):
                set_target_from_selection_parent(item['annotation'], task)

            if item['count'] >= 2:  # 2 matching transcriptions required
                final_transcriptions.append(item['annotation'])
            elif task.n_answers < 10:  # update required answers otherwise
                task.n_answers = task.n_answers + 1
                task_repo.update(task)
                result.last_version = False

    # Set result
    info = dict(annotations=comments)
    if result.last_version:
        info['annotations'] += clusters + final_transcriptions
    result.info = info
    result_repo.update(result)
    results_cache.clear_cache()


def analyse_all(project_id):
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
