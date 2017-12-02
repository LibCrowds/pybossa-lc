# -*- coding: utf8 -*-
"""IIIF Annotation analysis module."""

import datetime
import itertools
from pybossa.core import project_repo, result_repo
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


def update_selector(anno, rect):
    """Update a media frag selector."""
    frag = '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'], rect['w'],
                                          rect['h'])
    anno['target']['selector']['value'] = frag
    anno['modified'] = datetime.datetime.now().isoformat()


def analyse(result_id):
    """Analyse a IIIF Annotation result."""
    result = result_repo.get(result_id)
    df = helpers.get_task_run_df(result.task_id)

    # Flatten annotations into a single list
    anno_list = df['info'].tolist()
    anno_list = list(itertools.chain.from_iterable(anno_list))
    result.info = dict(annotations=[])
    clusters = []
    comments = []

    for anno in anno_list:
        if anno['motivation'] == 'commenting':
            comments.append(anno)
            continue

        # Cluster regions
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

        else:  # pragma: no cover
            raise ValueError('Unhandled motivation')

    result.info['annotations'] = clusters + comments
    result_repo.update(result)


def analyse_all(project_id):
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
