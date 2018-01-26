# -*- coding: utf8 -*-
"""Analysis helpers module."""

import math
import numpy
import pandas
from rq import Queue
from pybossa.core import sentinel
from pybossa.jobs import send_mail


MAIL_QUEUE = Queue('email', connection=sentinel.master)


def drop_keys(task_run_df, keys):
    """Drop keys from the info fields of a task run dataframe."""
    keyset = set()
    for i in range(len(task_run_df)):
        for k in task_run_df.iloc[i].keys():
            keyset.add(k)
    keys = [k for k in keyset if k not in keys]
    return task_run_df[keys]


def drop_empty_rows(task_run_df):
    """Drop rows that contain no data."""
    task_run_df = task_run_df.replace('', numpy.nan)
    task_run_df = task_run_df.dropna(how='all')
    return task_run_df


def has_n_matches(task_run_df, n_task_runs, match_percentage):
    """Check if n percent of answers match for each key."""
    required_matches = int(math.ceil(n_task_runs * (match_percentage / 100.0)))

    # Replace NaN with the empty string
    task_run_df = task_run_df.replace(numpy.nan, '')

    for k in task_run_df.keys():
        if task_run_df[k].value_counts().max() < required_matches:
            return False
    return True


def get_task_run_df(task_id):
    """Load an Array of task runs into a dataframe."""
    from pybossa.core import task_repo
    task_runs = task_repo.filter_task_runs_by(task_id=task_id)
    data = [explode_info(tr) for tr in task_runs]
    index = [tr.__dict__['id'] for tr in task_runs]
    return pandas.DataFrame(data, index)


def explode_info(item):
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


def analyse_all(analysis_func, project_id):
    """Analyse all results for a project."""
    from pybossa.core import project_repo, result_repo
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id)
    for result in results:
        analysis_func(result.id)

    msg = {
        'recipients': project.owner.email_addr,
        'subject': 'Analysis complete',
        'body': u'''
            All results for {} have been analysed.
            '''.format(project.name)
    }
    MAIL_QUEUE.enqueue(send_mail, msg)


def analyse_empty(analysis_func, project_id):
    """Analyse all empty results for a project."""
    from pybossa.core import project_repo, result_repo
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id)
    empty_results = [r for r in results if not r.info]
    for result in empty_results:
        analysis_func(result.id)

    msg = {
        'recipients': project.owner.email_addr,
        'subject': 'Analysis of all empty results complete',
        'body': u'''
            All empty results for {} have been analysed.
            '''.format(project.name)
    }
    MAIL_QUEUE.enqueue(send_mail, msg)


def get_analysis_rules(project_id):
    """Return the project template's analysis rules."""
    from pybossa.core import project_repo
    from ..cache import templates as templates_cache
    project = project_repo.get(project_id)
    template_id = project.info.get('template_id')
    if not template_id:
        return None

    tmpl = templates_cache.get_by_id(template_id)
    if not tmpl:
        return None

    return tmpl.get('rules')
