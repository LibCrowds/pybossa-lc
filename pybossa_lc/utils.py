# -*- coding: utf8 -*-
"""Utils module for pybossa-lc."""
from pybossa.core import project_repo
from pybossa.cache.projects import overall_progress


def get_enhanced_volumes(category):
    """Return the categories volumes enhanced with project data."""
    volumes = category.info.get('volumes', [])
    projects = project_repo.filter_by(category_id=category.id)

    for volume in volumes:
        vol_projects = [dict(id=p.id,
                             name=p.name,
                             short_name=p.short_name,
                             published=p.published,
                             overall_progress=overall_progress(p.id))
                        for p in projects
                        if p.info.get('volume_id') == volume['id']]
        completed_projects = [p for p in vol_projects
                              if p['overall_progress'] == 100]
        ongoing_projects = [p for p in vol_projects
                            if p['published'] and p not in completed_projects]
        volume['projects'] = vol_projects
        volume['n_completed_projects'] = len(completed_projects)
        volume['n_ongoing_projects'] = len(ongoing_projects)
    return volumes


def get_projects_with_unknown_volumes(category):
    """Return all projects not linked to a known volume."""
    volume_ids = [vol['id'] for vol in category.info.get('volumes', [])]
    projects = project_repo.filter_by(category_id=category.id)
    return [dict(id=p.id, name=p.name, short_name=p.short_name)
            for p in projects if not p.info.get('volume_id')
            or p.info.get('volume_id') not in volume_ids]
