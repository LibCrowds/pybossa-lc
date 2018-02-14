# -*- coding: utf8 -*-
"""Test fixtures."""

import random
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
        z3950_db = 'loc'  # from test settings
        self.z3950_tmpl = dict(database=z3950_db, institutions=['OCLC'])
        self.rules_tmpl = dict(concatenate=False, trim_punctuation=False,
                               whitespace='', case='',
                               target_from_select_parent=False,
                               date_format=True, dayfirst=True,
                               yearfirst=False)

    def create_template(self, task_tmpl=None, rules_tmpl=None):
        return dict(id=str(uuid.uuid4()), task=task_tmpl,
                    project=self.project_tmpl, rules=rules_tmpl)


class AnnotationFixtures(object):

    def create(self, motivation, tag=None, target=None, value=None):
        n = random.randint(1, 10)
        tag = tag or "tag_{}".format(n)
        source = target or "http://eg.com/iiif/book1/canvas/p{}".format(n)
        value = value or "Some Value {}".format(n)
        if motivation == 'describing':
            anno = {
                "motivation": "describing",
                "body": [
                    {
                        "type": "TextualBody",
                        "purpose": "describing",
                        "value": value,
                        "format": "text/plain"
                    },
                    {
                        "type": "TextualBody",
                        "purpose": "tagging",
                        "value": tag
                    }
                ],
                "target": source
            }
        elif motivation == 'tagging':
            anno = {
                "motivation": "tagging",
                "body": [
                    {
                        "type": "TextualBody",
                        "purpose": "tagging",
                        "value": tag
                    },
                ],
                "target": {
                    "source": source,
                    "selector": {
                        "conformsTo": "http://www.w3.org/TR/media-frags/",
                        "type": "FragmentSelector",
                        "value": value
                    }
                }
            }
        elif motivation == 'commenting':
            anno = {
                "motivation": "commenting",
                "body": {
                    "type": "TextualBody",
                    "purpose": "commenting",
                    "value": value,
                    "format": "text/plain"
                },
                "target": source
            }
            tag = None
        else:
            raise ValueError('Invalid motivation')

        return anno, tag, value, source
