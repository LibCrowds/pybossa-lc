# -*- coding: utf8 -*-
"""Analysis helpers module."""

import math
import numpy
import pandas
from rq import Queue
from pybossa.core import task_repo
from pybossa.core import sentinel
from pybossa.jobs import send_mail


MAIL_QUEUE = Queue('email', connection=sentinel.master)


def drop_keys(task_run_df, keys):
    """Drop keys from the info fields of a task run dataframe."""
    keyset = set()
    for i in range(len(task_run_df)):
        for k in task_run_df.iloc[i]['info'].keys():
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
    """Return a dataframe containing all task run info for a task."""
    task_runs = task_repo.filter_task_runs_by(task_id)
    return pandas.DataFrame(task_runs)


def send_email(msg):
    """Add email to PYBOSSA mail queue."""
    MAIL_QUEUE.enqueue(send_mail, msg)
