# -*- coding: utf8 -*-
"""API category module for pybossa-lc."""

from flask import Blueprint
from flask.ext.login import login_required
from pybossa.util import handle_content_type

from ..cache import templates as templates_cache

BLUEPRINT = Blueprint('templates', __name__)


@login_required
@BLUEPRINT.route('/')
def get_templates():
    """Return all templates."""
    templates = templates_cache.get_all()
    response = dict(templates=templates)
    return handle_content_type(response)
