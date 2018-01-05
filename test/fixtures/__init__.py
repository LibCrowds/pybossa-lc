# -*- coding: utf8 -*-
"""Test fixtures."""
import uuid


class TemplateFixtures:
    transcription_field = dict(label='Title', type='input', inputType='text',
                               placeholder='', model='title')
    project_tmpl = dict(name='My Project Type', tutorial='Do stuff',
                        description='This project is amazing', coowners=[],
                        category_id=None)
    iiif_select_tmpl = dict(tag='title', mode='select', objective='Mark up',
                            guidance='Do it now')
    iiif_transcribe_tmpl = dict(tag='title', mode='transcribe',
                                objective='Transcribe the title',
                                guidance='Do it now',
                                fields_schema=[transcription_field])
    z3950_db = 'loc' # from test settings
    z3950_tmpl = dict(database=z3950_db, institutions=['OCLC'])

    @classmethod
    def create_template(cls, task_tmpl=None):
        return dict(id=str(uuid.uuid4()), task=task_tmpl,
                    project=TemplateFixtures.project_tmpl)
