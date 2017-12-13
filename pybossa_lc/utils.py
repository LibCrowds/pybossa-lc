# -*- coding: utf8 -*-
"""Utilities module for pybossa-lc."""
import uuid


def get_template(category, template_id):
    """Return a valid template."""
    templates = [t for t in category.info.get('templates', [])
                 if t['id'] == template_id]
    return templates[0] if templates else None


def get_volume(category, volume_id):
    """Return a valid volume."""
    volumes = [v for v in category.info.get('volumes', [])
               if v['id'] == volume_id]
    return volumes[0] if volumes else None

def create_template(category, template_data):
    """Create a template."""
    _id = uuid.uuid4()
    templates = category.info.get('templates', [])
    templates[_id] = template_data