# -*- coding: utf8 -*-
"""Forms module for pybossa-lc."""
from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from pybossa.forms import validator as pb_validator


class TemplateFieldForm(Form):
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
    model = TextField('Model')


class ProjectTemplateForm(Form):
    name = TextField('Name', [validators.Required()])
    tag = TextField('Tag', [validators.Required(),
                            pb_validator.NotAllowedChars()])
    description = TextField('Description', [validators.Required()])
    objective = TextField('Objective', [validators.Required()])
    guidance = TextAreaField('Additional Guidance')
    tutorial = TextAreaField('Tutorial')
    mode = SelectField('Mode', choices=[
        ('select', 'Select'),
        ('transcribe', 'Transcribe')
    ])
