# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

import time
from pybossa.core import project_repo, result_repo

from . import helpers


MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'comments']


def analyse(result_id):
    """Analyse Z39.50 results."""
    result = result_repo.get(result_id)

    # Filter the valid task run keys
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]

    # Initialise the result with empty values for each task run key
    result.info = {k: "" for k in df.keys()}

    # Check if there are any non-empty answers
    df = helpers.drop_empty_rows(df)
    has_answers = not df.empty

    # Check if the match percentage is met
    n_task_runs = len(df.index)
    has_matches = helpers.has_n_matches(df, n_task_runs, MATCH_PERCENTAGE)

    # Store the matching result if match percentage met
    if has_answers and has_matches:
        for k in df.keys():
            result.info[k] = df[k].value_counts().idxmax()

    # Mark for further checking if match percentage not met
    elif has_answers:
        result.last_version = False

    result_repo.save(result)


def analyse_all(project_id):
    """Analyse all Z39.50 results."""
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id)
    for result in results:
        analyse(result)

    helpers.send_email({
        'recipients': project.owner.email_addr,
        'subject': 'Analysis complete',
        'body': '''
            All {0} results for {1} have been analysed.
            '''.format(len(results), project.name)
    })
