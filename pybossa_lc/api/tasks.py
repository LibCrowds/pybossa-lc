# -*- coding: utf8 -*-
"""API tasks module for pybossa-lc."""

import requests
from flask import Blueprint, abort
from pybossa.core import task_repo
from pybossa.util import handle_content_type


BLUEPRINT = Blueprint('lc_tasks', __name__)


@BLUEPRINT.route('/<int:task_id>/manifest')
def get_manifest(task_id):
    """Get the IIIF manifest for the task.

    As we're allowing any manifest to be loaded we can't rely on the
    presentation servers to have implemented CORS headers properly. This
    function is a proxy for retrieving the manifests from the server-side.
    """
    task = task_repo.get_task(task_id)
    if not task:
        abort(404)

    manifest_uri = task.info.get('manifest')
    if not manifest_uri:
        abort(404)

    manifest = requests.get(manifest_uri).json()
    return handle_content_type(manifest)
