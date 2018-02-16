# -*- coding: utf8 -*-
"""IIIF Annotation analysis module."""

import datetime
import itertools

from . import helpers


N_MATCHING_TRANSCRIPTIONS = 2


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
                value = helpers.normalise_transcription(item['value'], rules)
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


def analyse(result_id):
    """Analyse a IIIF Annotation result."""
    from pybossa.core import result_repo, task_repo
    result = result_repo.get(result_id)
    task = task_repo.get_task(result.task_id)
    df = helpers.get_task_run_df(result.task_id)

    # Flatten all annotations for the task into a single list
    anno_list = df['info'].tolist()
    anno_list = list(itertools.chain.from_iterable(anno_list))

    # Seperate different annotation types
    clusters = helpers.cluster_tagging_annotations(anno_list)
    comments = [anno for anno in anno_list
                if anno['motivation'] == 'commenting']
    transcriptions = [anno for anno in anno_list
                      if anno['motivation'] == 'describing']

    # Process transcriptions
    final_transcriptions = []
    if transcriptions:
        tmpl = helpers.get_project_template(result.project_id)
        rules = tmpl.get('rules')

        merged_transcriptions = merge_transcriptions(transcriptions, rules)
        for tag in merged_transcriptions:
            item = merged_transcriptions[tag]

            # Set annotation target from a selection parent
            if rules and rules.get('target_from_select_parent'):
                set_target_from_selection_parent(item['annotation'], task)

            # Save matching transcriptions or ask for another answer
            if item['count'] >= N_MATCHING_TRANSCRIPTIONS:
                final_transcriptions.append(item['annotation'])
            else:
                helpers.update_n_answers_required(task)

    # Set the result
    new_annotations = comments
    if result.last_version:
        new_annotations += clusters + final_transcriptions

    result.last_version = True
    result.info = dict(annotations=new_annotations)
    result_repo.update(result)


def analyse_all(project_id):
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
