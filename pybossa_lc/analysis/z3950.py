# -*- coding: utf8 -*-
"""Z39.50 analysis module."""

from . import helpers


MATCH_PERCENTAGE = 60
VALID_KEYS = ['oclc', 'shelfmark', 'control_number', 'reference', 'comments']


def get_old_info(result_info):
    """Return any info stored in the old analysis module format."""
    old_keys = ['oclc', 'shelfmark', 'oclc-option', 'shelfmark-option',
                'comments-option']
    old_info = None
    if result_info and any(key in result_info for key in old_keys):

        def replace_old_key(old_key, new_key):
            old = result_info.get(old_key)
            old_analysed = result_info.get('{}-option'.format(old_key))
            new = result_info.get(new_key)
            return old_analysed if old_analysed else new if new else old

        old_info = {
            'control_number': replace_old_key('oclc', 'control_number'),
            'reference': replace_old_key('shelfmark', 'reference'),
            'comments': replace_old_key('comments', 'comments'),
        }
    return old_info


def analyse(result_id, _all=False):
    """Analyse Z39.50 results."""
    from pybossa.core import result_repo
    result = result_repo.get(result_id)
    new_annotations = []
    target = helpers.get_task_target(result.task_id)

    # Update old method of verification
    if result.info == 'Unverified':
        result.info = {}

    # Store any old info as it may already have been manually verified
    old_info = get_old_info(result.info)
    if old_info:
        comment_anno = helpers.create_commenting_anno(target,
                                                      old_info['comments'])
        ctrl_anno = helpers.create_describing_anno(target,
                                                   old_info['control_number'],
                                                   'control_number')
        ref_anno = helpers.create_describing_anno(target,
                                                  old_info['reference'],
                                                  'reference')
        new_annotations = [comment_anno, ctrl_anno, ref_anno]
        result.info = dict(annotations=new_annotations)
        result_repo.update(result)
        return

    # Don't update if info field populated and _all=False
    if result.info and not _all:
        return

    # Check for any manually modified annotations
    old_annos = [] if not result.info else result.info.get('annotations', [])
    mod_ctrl = helpers.get_modified_annos(old_annos, 'control_number')
    if mod_ctrl:
        new_annotations += mod_ctrl
    mod_ref = helpers.get_modified_annos(old_annos, 'reference')
    if mod_ref:
        new_annotations += mod_ref

    # Filter the valid task run keys
    df = helpers.get_task_run_df(result.task_id)
    df = df.loc[:, df.columns.isin(VALID_KEYS)]

    # Replace deprecated keys
    df = helpers.replace_df_keys(df, oclc='control_number',
                                 shelfmark='reference')

    # Verify that the required columns exist
    required_keys = ['control_number', 'reference', 'comments']
    if not all(key in df for key in required_keys):
        raise ValueError('Missing required keys')

    # Assume last version for now
    result.last_version = True

    # Check for any comments (which might signify further checks required)
    comments = [comment for comment in df['comments'].tolist() if comment]
    if comments:
        print comments
        for value in comments:
            comment_anno = helpers.create_commenting_anno(target, value)
            new_annotations.append(comment_anno)
        result.last_version = False

    # With comments handled, focus on control_number and reference
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
        reference = df['reference'].value_counts().idxmax()
        if not mod_ctrl:
            ctrl_anno = helpers.create_describing_anno(target, control_number,
                                                       'control_number')
            new_annotations.append(ctrl_anno)

        if not mod_ref:
            ref_anno = helpers.create_describing_anno(target, reference,
                                                      'reference')
            new_annotations.append(ref_anno)

    # Mark for further checking if match percentage not met
    elif has_answers:
        result.last_version = False

    result.info = dict(annotations=new_annotations)
    result_repo.update(result)


def analyse_all(project_id):
    """Analyse all results."""
    helpers.analyse_all(analyse, project_id)


def analyse_empty(project_id):
    """Analyse all empty results."""
    helpers.analyse_empty(analyse, project_id)
