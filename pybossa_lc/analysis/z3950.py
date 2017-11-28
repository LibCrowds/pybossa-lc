# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

import time
from pybossa_lc.analysis import helpers
from pybossa.core import result_repo


MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'comments']


def analyse(result):
    """Analyse Z39.50 results."""
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]
    df = helpers.drop_empty_rows(df)
    n_task_runs = len(df.index)

    # Initialise the result
    defaults = {k: "" for k in df.keys()}
    defaults['analysis_complete'] = True
    result.info = dict(defaults)

    has_answers = not df.empty
    has_matches = helpers.has_n_matches(df, n_task_runs, MATCH_PERCENTAGE)

    # Matching answers
    if has_answers and has_matches:
        for k in df.keys():
            result.info[k] = df[k].value_counts().idxmax()

    # Varied answers
    elif has_answers:
        result.info['analysis_complete'] = False
    result_repo.save(result)


def analyse_all(**kwargs):
    """Analyse all Z39.50 results."""
    for result in results:
        analyse(result)

    helpers.send_email({
        'recipients': project.owner.email_addr,
        'subject': 'Analysis complete',
        'body': '''
            All {0} results for {1} have been analysed.
            '''.format(len(results), project.name)
    })
