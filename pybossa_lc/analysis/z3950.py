# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

import time
from pybossa.core import project_repo, result_repo
from pybossa.core import sentinel
from pybossa.jobs import send_mail
from rq import Queue

from . import helpers


MAIL_QUEUE = Queue('email', connection=sentinel.master)
MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'control_number', 'reference', 'comments']


def analyse(result_id):
    """Analyse Z39.50 results."""
    result = result_repo.get(result_id)

    # Filter the valid task run keys
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]

    # Rename old Convert-a-Card specific keys
    df = df.rename(columns={
        'oclc': 'control_number',
        'shelfmark': 'reference'
    })

    # Initialise the result with empty values
    result.info = {k: "" for k in df.keys()}

    # Check for any comments
    if not helpers.drop_empty_rows(df['comments']).empty:
        result_repo.update(result)
        result.last_version = False
        return

    # With no comments, focus on control_number and reference
    df = df[['control_number', 'reference']]

    # Check if there are any non-empty answers
    df = helpers.drop_empty_rows(df)
    has_answers = not df.empty

    # Check if the match percentage is met
    n_task_runs = len(result.task_run_ids)
    has_matches = helpers.has_n_matches(df, n_task_runs, MATCH_PERCENTAGE)

    # Store most common answers for each key if match percentage met
    if has_answers and has_matches:
        control_number = df['control_number'].value_counts().idxmax()
        result.info['control_number'] = control_number
        reference = df['reference'].value_counts().idxmax()
        result.info['reference'] = reference

    # Mark for further checking if match percentage not met
    elif has_answers:
        result.last_version = False

    result_repo.update(result)


def analyse_all(project_id):
    """Analyse all Z39.50 results."""
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id)
    for result in results:
        analyse(result)

    msg = {
        'recipients': project.owner.email_addr,
        'subject': 'Analysis complete',
        'body': u'''
            All {0} results for {1} have been analysed.
            '''.format(len(results), project.name)
    }
    MAIL_QUEUE.enqueue(send_mail, msg)


def analyse_empty(project_id):
    """Analyse all empty Z39.50 results."""
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id, info=None)
    for result in results:
        analyse(result)

    msg = {
        'recipients': project.owner.email_addr,
        'subject': 'Analysis of all empty results complete',
        'body': u'''
            All {0} empty results for {1} have been analysed.
            '''.format(len(results), project.name)
    }
    MAIL_QUEUE.enqueue(send_mail, msg)
