# -*- coding: utf8 -*-
"""Test fixtures."""
import uuid


class TemplateFixtures(object):

    def __init__(self, category):
        transcription_field = dict(label='Title', type='input', model='title',
                                   placeholder='', inputType='text')
        self.project_tmpl = dict(name='My Project Type', tutorial='Do stuff',
                                 description='This project is amazing',
                                 category_id=category.id)
        self.iiif_select_tmpl = dict(tag='title', mode='select',
                                     guidance='Do it now', objective='Mark up')
        self.iiif_transcribe_tmpl = dict(tag='title', mode='transcribe',
                                         objective='Transcribe the title',
                                         guidance='Do it now',
                                         fields_schema=[transcription_field])
        z3950_db = 'loc' # from test settings
        self.z3950_tmpl = dict(database=z3950_db, institutions=['OCLC'])
        self.rules_tmpl = dict(concatenate=True, trimpunctuation=True,
                               whitespace=False, titlecase=False)

    def create_template(self, task_tmpl=None, rules_tmpl=None):
        return dict(id=str(uuid.uuid4()), task=task_tmpl,
                    project=self.project_tmpl, rules=rules_tmpl)
