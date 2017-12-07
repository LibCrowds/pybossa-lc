# -*- coding: utf8 -*-
"""API projects module for pybossa-lc."""

import re
import json
from flask import Response, Blueprint, flash, request, abort, current_app
from pybossa.core import csrf, project_repo
from pybossa.model.project import Project
from flask.ext.login import login_required, current_user
from pybossa.auth import ensure_authorized_to
from pybossa.core import importer
from pybossa.importers import BulkImportException
from pybossa.view.projects import _import_tasks


BLUEPRINT = Blueprint('projects', __name__)


@csrf.exempt
@login_required
@BLUEPRINT.route('/create', methods=['POST'])
def create():
    """Create a LibCrowds project."""
    required_args = ['collection', 'volume', 'template']
    data = json.loads(request.data)
    if not all(arg in data for arg in required_args):
        abort(400)

    volume = data['volume']
    template = data['template']
    collection = data['collection']
    category = project_repo.get_category(collection.get('id'))
    if not category:
        abort(404)

    ensure_authorized_to('create', Project)

    name = '{0}: {1}'.format(template['name'], volume['name'])
    badchars = r"([$#%·:,.~!¡?\"¿'=)(!&\/|]+)"
    shortname = re.sub(badchars, '', name.lower().strip()).replace(' ', '_')
    presenter = collection['info']['presenter']
    webhook = '{0}libcrowds/analysis/{1}'.format(request.url_root, presenter)


    project = Project(name=name,
                      short_name=shortname,
                      description=template['description'],
                      long_description='',
                      owner_id=current_user.id,
                      info={
                          'volume': volume,
                          'template': template
                      },
                      webhook=webhook,
                      category_id=category.id,
                      owners_ids=[current_user.id])

    project_repo.save(project)
    volume['type'] = volume['importer']
    volume['template'] = 'template'
    try:
        print volume
        return _import_tasks(project, **volume)
    except BulkImportException as err_msg:
        flash(err_msg, 'error')
    except Exception as inst:  # pragma: no cover
        current_app.logger.error(inst)
        msg = 'Oops! Looks like there was an error!'
        flash(msg, 'error')

    res = {
        'status': 'success',
        'message': '''Your project is now being generated, you will recieve an
            email when this is complete.''',
        'queued': False
    }
    return Response(json.dumps(res), 200, mimetype='application/json')
