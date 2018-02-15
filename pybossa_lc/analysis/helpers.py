# -*- coding: utf8 -*-
"""Analysis helpers module."""

import math
import numpy
import string
import pandas
import dateutil
import dateutil.parser
from datetime import datetime
from titlecase import titlecase
from flask import current_app
from pybossa.jobs import project_export


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
        analysis_func(result.id, _all=True)
    if results:
        project_export(project.id)


def analyse_empty(analysis_func, project_id):
    """Analyse all empty results for a project."""
    from pybossa.core import project_repo, result_repo
    project = project_repo.get(project_id)
    results = result_repo.filter_by(project_id=project_id)
    empty_results = [r for r in results if not r.info]
    for result in empty_results:
        analysis_func(result.id)
    if empty_results:
        project_export(project.id)


def get_analysis_rules(project_id):
    """Return the project template's analysis rules."""
    from pybossa.core import project_repo
    from ..cache import templates as templates_cache
    project = project_repo.get(project_id)
    template_id = project.info.get('template_id')
    if not template_id:
        return None

    tmpl = templates_cache.get_by_id(template_id)
    if not tmpl:  # pragma: no-cover
        return None

    return tmpl.get('rules')


def normalise_transcription(value, rules):
    """Normalise value according to the specified analysis rules."""
    if not rules or not isinstance(value, basestring):
        return value

    normalised = value

    # Normalise case
    if rules.get('case') == 'title':
        normalised = titlecase(normalised.lower())
    elif rules.get('case') == 'lower':
        normalised = normalised.lower()
    elif rules.get('case') == 'upper':
        normalised = normalised.upper()

    # Normalise whitespace
    if rules.get('whitespace') == 'normalise':
        normalised = " ".join(normalised.split())
    elif rules.get('whitespace') == 'underscore':
        normalised = " ".join(normalised.split()).replace(' ', '_')
    elif rules.get('whitespace') == 'full_stop':
        normalised = " ".join(normalised.split()).replace(' ', '.')

    # Normalise dates
    if rules.get('date_format'):
        dayfirst = rules.get('dayfirst', False)
        yearfirst = rules.get('yearfirst', False)
        try:
            ts = dateutil.parser.parse(normalised, dayfirst=dayfirst,
                                       yearfirst=yearfirst)
        except (ValueError, TypeError):
            return ''
        normalised = ts.isoformat()[:10]

    # Normalise punctuation
    if rules.get('trim_punctuation'):
        normalised = normalised.strip(string.punctuation)
    return normalised


def update_n_answers_required(task, max_answers=10):
    """Update number of answers required for a task, if already completed."""
    from pybossa.core import task_repo
    task_runs = task_repo.filter_task_runs_by(task_id=task.id)
    n_task_runs = len(task_runs)
    if task.n_answers < max_answers:
        task.state = "ongoing"
        if n_task_runs >= task.n_answers:
            task.n_answers = task.n_answers + 1
    else:
        task.state = "completed"
    task_repo.update(task)


def replace_df_keys(df, **kwargs):
    """Replace a set of keys in a dataframe."""
    if not kwargs:
        return df
    df = df.rename(columns=kwargs)
    def sjoin(x): return ';'.join(x[x.notnull()].astype(str))
    df = df.groupby(level=0, axis=1).apply(lambda x: x.apply(sjoin, axis=1))
    return df


def get_task_target(task_id):
    """Get the target for different types of task."""
    from pybossa.core import task_repo
    task = task_repo.get_task(task_id)
    if 'target' in task.info:  # IIF Annotation tasks
        return task.info['target']
    elif 'link' in task.info:  # Flickr tasks
        return task.info['link']


def get_xsd_datetime():
    """Return timestamp expressed in the UTC xsd:datetime format."""
    return datetime.utcnow().isoformat()[:-7] + 'Z'


def get_anno_generator():
    """Return a reference to the LibCrowds software."""
    spa_server_name = current_app.config.get('SPA_SERVER_NAME')
    return {
        "id": spa_server_name,
        "type": "Software",
        "name": "LibCrowds",
        "homepage": spa_server_name
    }


def get_anno_base(motivation):
    """Return the base fo ra new Web Annotation."""
    ts_now = get_xsd_datetime()
    return {
        "@context": "http://www.w3.org/ns/anno.jsonld",
        "type": "Annotation",
        "motivation": motivation,
        "created": ts_now,
        "generated": ts_now,
        "generator": get_anno_generator(),
        "modified": ts_now
    }


def create_commenting_anno(target, value):
    """Create a Web Annotation with the commenting motivation."""
    anno = get_anno_base('commenting')
    anno['target'] = target
    anno['body'] = {
        "type": "TextualBody",
        "value": value,
        "purpose": "commenting",
        "format": "text/plain"
    }
    return anno


def create_tagging_anno(target, value):
    """Create a Web Annotation with the tagging motivation."""
    anno = get_anno_base('tagging')
    anno['target'] = target
    anno['body'] = {
        "type": "TextualBody",
        "purpose": "tagging",
        "value": value
    }
    return anno


def create_describing_anno(target, value, tag):
    """Create a Web Annotation with the describing motivation."""
    anno = get_anno_base('describing')
    anno['target'] = target
    anno['body'] = [
        {
            "type": "TextualBody",
            "purpose": "describing",
            "value": value,
            "format": "text/plain"
        },
        {
            "type": "TextualBody",
            "purpose": "tagging",
            "value": tag
        }
    ]
    return anno
