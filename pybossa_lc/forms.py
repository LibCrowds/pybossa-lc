# -*- coding: utf8 -*-
"""Forms module for pybossa-lc."""

from flask_wtf import Form
from wtforms import TextField, TextAreaField, SelectField, validators
from wtforms import IntegerField, FieldList, FormField, BooleanField
from wtforms.validators import ValidationError
from wtforms.widgets import HiddenInput
from pybossa.forms import validator as pb_validator
from pybossa.core import project_repo

from .cache import templates as templates_cache


class UniqueTemplateField(object):
    """Checks for a unique template field."""

    def __init__(self, section, field_name, message=None):
        self.field_name = field_name
        self.section = section
        if not message:  # pragma: no cover
            message = '''A template with this {} already exists
                      '''.format(field_name)
        self.message = message

    def __call__(self, form, form_field):
        tmpl_id = form.id.data
        templates = templates_cache.get_all()
        exists = [tmpl for tmpl in templates
                  if tmpl[self.section] and
                  tmpl[self.section][self.field_name] == form_field.data and
                  (not tmpl_id or tmpl_id != tmpl['id'])]
        if exists:
            raise ValidationError(self.message)


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
                  if vol[self.field_name] == form_field.data and
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


class IIIFAnnotationTemplateForm(Form):
    """A form for creating task templates for IIIF annotation projects."""
    id = TextField(label=None, widget=HiddenInput())
    tag_pattern = r'^[a-z0-9_]*$'
    tag_msg = '''Must use a combination of lowercase characters, numbers or
              underscores'''
    tag = TextField('Tag', [validators.Required(),
                            UniqueTemplateField('task', 'tag'),
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
    titlecase = BooleanField()
    whitespace = BooleanField()
    trim_punctuation = BooleanField()
    concatenate = BooleanField()
    target_from_select_parent = BooleanField()


class ProjectForm(Form):
    """A form for creating projects from templates."""
    volume_id = SelectField('Volume')
    template_id = SelectField('Template')
    parent_id = SelectField('Parent Project', coerce=int)


class VolumeForm(Form):
    """A form for creating volumes."""
    id = TextField(label=None, widget=HiddenInput())
    category_id = IntegerField(label=None, widget=HiddenInput())
    name = TextField('Name', [validators.Required(),
                              UniqueVolumeField('name')])
    source = TextField('Source', [validators.Required(),
                                  UniqueVolumeField('source')])
