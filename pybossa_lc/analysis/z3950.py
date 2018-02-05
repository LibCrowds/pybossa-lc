# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

from . import helpers


MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'control_number', 'reference', 'comments']


def analyse(result_id):
    """Analyse Z39.50 results."""
    from pybossa.core import result_repo
    result = result_repo.get(result_id)

    # Update old method of verification
    if result.info == 'Unverified':
        result.info = {}

    # Fix any bad keys from previous analysis module
    old_keys = ['oclc', 'shelfmark', 'oclc-option', 'shelfmark-option',
                'comments-option']
    if result.info and any(key in result.info for key in old_keys):

        def replace_old_key(old_key, new_key):
            old = result.info.get(old_key)
            old_analysed = result.info.get('{}-option'.format(old_key))
            new = result.info.get(new_key)
            return new if new else old_analysed if old_analysed else old

        new_info = {
            'control_number': replace_old_key('oclc', 'control_number'),
            'reference': replace_old_key('shelfmark', 'reference'),
            'comments': replace_old_key('comments', 'comments'),
        }
        result.info = new_info
        result_repo.update(result)

    # Don't update if info field populated (ie. answer already verified)
    if result.info:
        return

    # Filter the valid task run keys
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]

    # Rename old keys from task runs
    df = df.rename(columns={
        'oclc': 'control_number',
        'shelfmark': 'reference'
    })

    # Verify that the required columns exist
    required_keys = ['control_number', 'reference', 'comments']
    if not all(key in df for key in required_keys):
        raise ValueError('Missing required keys')

    # Initialise the result with empty values
    result.info = {k: "" for k in df.keys()}

    # Assume last version for now
    result.last_version = True

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
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
