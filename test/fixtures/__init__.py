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

    @staticmethod
    def create_tagging_anno(suffix):
        """Create a tagging annotation."""
        tag = "{0}_{1}".format(tag, suffix)
        value = "?xywh={0},{0},{0},{0}".format(suffix)
        source = "http://example.org/iiif/book1/canvas/p{0}".format(suffix)
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
        return anno, tag, value, source

    @staticmethod
    def create_describing_anno(suffix, tag="tag"):
        """Create a describing annotation."""
        tag = "{0}_{1}".format(tag, suffix)
        value = "Some Value {}".format(suffix)
        source = "http://example.org/iiif/book1/canvas/p{}".format(suffix)
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
        return anno, tag, value, source

    @staticmethod
    def create_commenting_anno(suffix):
        """Create a commenting annotation."""
        value = "Some Value {}".format(suffix)
        source = "http://example.org/iiif/book1/canvas/p{}".format(suffix)
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
        return anno, None, value, source
