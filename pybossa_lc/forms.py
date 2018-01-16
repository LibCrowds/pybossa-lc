# -*- coding: utf8 -*-
"""Forms module for pybossa-lc."""

from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from wtforms import IntegerField, FieldList, FormField, BooleanField
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


class ProjectTemplateForm(Form):
    """Form for creating project templates."""
    name = TextField('Name', [validators.Required()])
    description = TextField('Description', [validators.Required()])
    tutorial = TextAreaField('Tutorial')
    category_id = SelectField('Category', coerce=int)


class IIIFAnnotationTemplateForm(Form):
    """A form for creating task templates for IIIF annotation projects."""
    tag = TextField('Tag', [validators.Required(),
                            pb_validator.NotAllowedChars()])
    objective = TextField('Objective', [validators.Required()])
    guidance = TextAreaField('Additional Guidance')
    mode = SelectField('Mode', choices=[
        ('select', 'Select'),
        ('transcribe', 'Transcribe')
    ])
    fields_schema = FieldList(FormField(FieldsSchemaForm))


class Z3950TemplateForm(Form):
    """A form for creating task templates for Z39.50 projects."""
    database = SelectField('Database', choices=[])
    institutions = FieldList(TextField('Institution code',
                                       [validators.Required()]))


class NormalisationRulesForm(Form):
    """A form for setting normalisation rules for transcriptions."""
    titlecase = BooleanField('Convert to title case')
    whitespace = BooleanField('Normalise whitespace')
    trimpunctuation = BooleanField('Trim punctuation')
    concatenate = BooleanField('Concatenate Fields')


class ProjectForm(Form):
    """A form for creating projects from templates."""
    volume_id = SelectField('Volume')
    template_id = SelectField('Template')
    parent_id = SelectField('Parent Project', coerce=int)


class VolumeForm(Form):
    """A form for creating volumes."""
    name = TextField('Name', [validators.Required()])
    source = TextField('Source', [validators.Required()])
