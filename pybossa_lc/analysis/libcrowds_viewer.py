# -*- coding: utf8 -*-
"""LibCrowds Viewer analysis module."""

import time
import datetime
import itertools
import enki
from libcrowds_analyst.analysis import helpers
from pybossa.core import project_repo
from pybossa.auth import ensure_authorized_to


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
    """Update amedia frag selector."""
    frag = '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'], rect['w'],
                                          rect['h'])
    anno['target']['selector']['value'] = frag
    anno['modified'] = datetime.datetime.now().isoformat()


def analyse_selections(api_key, endpoint, project_id, result_id, path, doi,
                       project_short_name, throttle, **kwargs):
    """Analyse In the Spotlight selection results."""
    e = enki.Enki(api_key, endpoint, project_short_name, all=1)
    result = enki.pbclient.find_results(project_id, id=result_id, limit=1,
                                        all=1)[0]
    df = helpers.get_task_run_df(e, result.task_id)

    # Flatten annotations into a single list
    anno_list = df['info'].tolist()
    anno_list = list(itertools.chain.from_iterable(anno_list))
    defaults = {'annotations': []}
    result.info = helpers.init_result_info(doi, path, defaults)
    clusters = []
    comments = []

    # Cluster similar regions
    for anno in anno_list:
        if anno['motivation'] == 'commenting':
            comments.append(anno)
            continue

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
    enki.pbclient.update_result(result)
    time.sleep(throttle)


def analyse_all_selections(**kwargs):
    """Analyse all results."""
    ensure_authorized_to('update', project)
    project = project_repo.get_by_shortname(kwargs['project_short_name'])
    results = results_repo.filter_by(project_id=project.id)
    results = object_loader.load(enki.pbclient.find_results,
                                 project_id=e.project.id, all=1)
    for result in results:
        kwargs['project_id'] = e.project.id
        kwargs['result_id'] = result.id
        analyse_selections(**kwargs.copy())

    helpers.send_mail({
        'recipients': kwargs['mail_recipients'],
        'subject': 'Analysis complete',
        'body': '''
            All {0} results for {1} have been analysed.
            '''.format(len(results), e.project.name)
    })