# -*- coding: utf8 -*-
"""Template fixtures."""

from pybossa.model import make_uuid


class TemplateFixtures(object):

    def __init__(self, category):
        self.category = category
        transcription_field = dict(label='Title', type='input', model='title',
                                   placeholder='', inputType='text')
        self.iiif_select_tmpl = dict(tag='title', mode='select',
                                     guidance='Do it now', objective='Mark up')
        self.iiif_transcribe_tmpl = dict(tag='title', mode='transcribe',
                                         objective='Transcribe the title',
                                         guidance='Do it now',
                                         fields_schema=[transcription_field])
        z3950_db = 'loc'  # from test settings
        self.z3950_tmpl = dict(database=z3950_db, institutions=['OCLC'])
        self.rules_tmpl = dict(trim_punctuation=False,
                               whitespace='',
                               case='',
                               date_format=True,
                               dayfirst=True,
                               yearfirst=False,
                               remove_fragment_selector=False)

    def create(self, task_tmpl=None, rules_tmpl=None):
        task = task_tmpl or {}
        rules = task_tmpl or {}
        return dict(id=make_uuid(),
                    name='My Project Type',
                    tutorial='Do stuff',
                    description='This project is amazing',
                    parent_template_id=None,
                    importer=None,
                    min_answers=3,
                    max_answers=3,
                    task=task,
                    rules=rules)
