# -*- coding: utf8 -*-
"""Forms module for pybossa-lc."""

from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from wtforms import IntegerField, FieldList, FormField
from wtforms.widgets import HiddenInput
from pybossa.forms import validator as pb_validator


class FieldsSchemaForm(Form):
    """A form for creating a field schemas."""
    label = TextField('Label', [validators.Required()])
    type = SelectField('Mode', choices=[
        ('input', 'Input'),
        ('textArea', 'Text Area'),
        ('checkbox', 'Checkbox')
    ])
    inputType = SelectField('Mode', choices=[
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('url', 'URL')
    ])
    placeholder = TextField('Placeholder')
    model = TextField('Model', [validators.Required(),
                                pb_validator.NotAllowedChars()])


class BaseTemplateForm(Form):
    """Base form for creating project templates."""
    id = IntegerField(label=None, widget=HiddenInput())
    name = TextField('Name', [validators.Required()])
    description = TextField('Description', [validators.Required()])
    tutorial = TextAreaField('Tutorial')
    coowners = FieldList(IntegerField('Coowners'))


class IIIFAnnotationTemplateForm(BaseTemplateForm):
    """A form for creating project templates for IIIF annotation projects."""
    tag = TextField('Tag', [validators.Required(),
                            pb_validator.NotAllowedChars()])
    objective = TextField('Objective', [validators.Required()])
    guidance = TextAreaField('Additional Guidance')
    mode = SelectField('Mode', choices=[
        ('select', 'Select'),
        ('transcribe', 'Transcribe')
    ])
    fields_schema = FieldList(FormField(FieldsSchemaForm), min_entries=1)


class Z3950TemplateForm(BaseTemplateForm):
    """A form for creating project templates for Z39.50 projects."""
    database = SelectField('Database', choices=[])
    institutions = FieldList(TextField('Institution code',
                                       [validators.Required()]),
                             min_entries=1)
