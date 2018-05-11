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


class FieldsSchemaForm(Form):
    """A form for creating a field schemas."""
    label = TextField('Label', [validators.Required()])
    type = SelectField('Mode', choices=[
        ('input', 'Input'),
        ('textArea', 'Text Area'),
        ('checkbox', 'Checkbox')
    ])
    inputType = SelectField('Mode', default='text', choices=[
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
    parent_template_id = SelectField('Parent', choices=[
        ('None', '')
    ])
    min_answers = IntegerField('Min Answers', [validators.Required()],
                               default=3)
    max_answers = IntegerField('Max Answers', [validators.Required()],
                               default=3)


class IIIFAnnotationTemplateForm(Form):
    """A form for creating task templates for IIIF annotation projects."""
    tag_pattern = r'^[a-z0-9_]*$'
    tag_msg = '''Must use a combination of lowercase characters, numbers or
              underscores'''
    tag = TextField('Tag', [validators.Required(),
                            validators.Regexp(tag_pattern, message=tag_msg)])
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


class AnalysisRulesForm(Form):
    """A form for setting normalisation rules for transcriptions."""
    whitespace = SelectField('Mode', choices=[
        ('', 'Do not modify'),
        ('normalise', 'Normalise'),
        ('underscore', 'Replace with underscores'),
        ('full_stop', 'Replace with full stops')
    ], default='')
    case = SelectField('Mode', choices=[
        ('', 'Do not modify'),
        ('title', 'Titlecase'),
        ('lower', 'Lowercase'),
        ('upper', 'Uppercase'),
    ], default='')
    trim_punctuation = BooleanField()
    date_format = BooleanField()
    dayfirst = BooleanField()
    yearfirst = BooleanField()
    remove_fragment_selector = BooleanField()


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


class IIIFSettingsForm(Form):
    """A form for IIIF settings."""
    image_api_uri = TextField('API URI',
                              [validators.Required(), validators.URL()])
    image_api_version = DecimalField('Version', [validators.Required()],
                                     places=1, default=2.0)
    compliance_validators = [
        validators.NumberRange(min=0, max=2)
    ]
    image_api_compliance = IntegerField('Compliance Level',
                                        compliance_validators, default=0)


class CustomExportForm(Form):
    """A form for creating a custom export."""
    id = TextField(label=None, widget=HiddenInput())
    short_name = TextField('Short Name', [validators.Required(),
                                          pb_validator.NotAllowedChars()])
    name = TextField('Name', [validators.Required()])
    root_template_id = SelectField('Root Template', choices=[
        ('None', '')
    ])
    motivation = SelectField('Motivation', choices=[
        ('tagging', 'Tagging'),
        ('describing', 'Describing'),
        ('commenting', 'Commenting')
    ])
    include = SelectMultipleField('Include', choices=[
        ('None', '')
    ])
