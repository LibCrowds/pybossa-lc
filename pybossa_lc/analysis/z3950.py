# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

from . import helpers


MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'control_number', 'reference', 'comments']


def analyse(result_id):
    """Analyse Z39.50 results."""
    from pybossa.core import result_repo
    from ..cache import results as results_cache
    result = result_repo.get(result_id)

    # Filter the valid task run keys
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]

    # Rename old specific keys
    df = df.rename(columns={
        'oclc': 'control_number',
        'shelfmark': 'reference'
    })

    # Initialise the result with empty values
    result.info = {k: "" for k in df.keys()}

    # Check for any comments (which might signify further checks required)
    if not helpers.drop_empty_rows(df['comments']).empty:
        result_repo.update(result)
        result.last_version = False
        return

    # With no comments, focus on control_number and reference
    df = df[['control_number', 'reference']]

    # Check if there are any non-empty answers
    df = helpers.drop_empty_rows(df)
    has_answers = not df.empty

    # Apply normalisation rules to reference
    rules = helpers.get_analysis_rules(result.project_id)
    norm_func = helpers.normalise_transcription
    df['reference'] = df['reference'].apply(lambda x: norm_func(x, rules))
    print df['reference']

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

    print result
    result_repo.update(result)
    results_cache.clear_cache()


def analyse_all(project_id):
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
