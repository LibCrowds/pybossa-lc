# -*- coding: utf8 -*-
"""API tasks module for pybossa-lc."""

import requests
from flask import Blueprint, abort, request
from pybossa.util import handle_content_type


BLUEPRINT = Blueprint('lc_proxy', __name__)


@BLUEPRINT.route('/')
def get():
    """Proxy a JSON get request.

    Primarily intended for IIIF manifests. as we're allowing any manifest to
    be loaded we can't rely on the presentation servers to have implemented
    CORS headers properly, so this function is used as a proxy for retrieving
    the manifests from the server-side.
    """
    url = request.args.get('url')
    if not url:
        abort(404)

    data = requests.get(url).json()
    return handle_content_type(data)
