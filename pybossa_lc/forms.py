# -*- coding: utf8 -*-
"""Forms module for pybossa-lc."""

from flask import current_app
from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from wtforms import IntegerField, FieldList, FormField, BooleanField
from wtforms import DecimalField, SelectMultipleField
from wtforms.validators import ValidationError
from wtforms.widgets import HiddenInput
from pybossa.forms import validator as pb_validator
from pybossa.core import project_repo


class UniqueVolumeField(object):
    """Checks for a unique volume field for a category."""

    def __init__(self, field_name, message=None):
        self.field_name = field_name
        if not message:  # pragma: no cover
            message = 'A volume with this {} already exists'.format(field_name)
        self.message = message

    def __call__(self, form, form_field):
        category_id = int(form.category_id.data)
        vol_id = form.id.data
        category = project_repo.get_category(category_id)
        volumes = category.info.get('volumes', [])
        exists = [vol for vol in volumes
                  if vol.get(self.field_name) and
                  vol[self.field_name] == form_field.data and
                  (not vol_id or vol_id != vol['id'])]

        if exists:
            raise ValidationError(self.message)


class ProjectForm(Form):
    """A form for creating projects from templates."""
    volume_id = SelectField('Volume')
    template_id = SelectField('Template')
    name_msg = "This name is already taken."
    name = TextField('Name',
                     [validators.Required(),
                      pb_validator.Unique(project_repo.get_by,
                                          'name',
                                          message=name_msg)])
    sn_msg = "This short name is already taken."
    short_name = TextField('Short Name',
                           [validators.Required(),
                            pb_validator.NotAllowedChars(),
                            pb_validator.Unique(project_repo.get_by,
                                                'short_name',
                                                message=sn_msg),
                            pb_validator.ReservedName('project', current_app)])


class VolumeForm(Form):
    """A form for creating volumes."""
    id = TextField(label=None, widget=HiddenInput())
    category_id = IntegerField(label=None, widget=HiddenInput())
    name = TextField('Name', [validators.Required(),
                              UniqueVolumeField('name')])
    short_name = TextField('Short Name', [validators.Required(),
                                          pb_validator.NotAllowedChars(),
                                          UniqueVolumeField('short_name')])
    importer = SelectField('Importer')
