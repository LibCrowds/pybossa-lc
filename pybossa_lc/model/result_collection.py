# -*- coding: utf8 -*-
"""ResultCollection model."""

from .base import Base


class ResultCollection(Base):
    """ResultCollection model."""

    def __init__(self, iri):
        super(ResultCollection, self).__init__(iri)

    def add_comment(self, result, target, value, user=None):
        """Add a commenting Annotation."""
        anno = self._get_commenting_annotation(result, target, value, user)
        self._create_annotation(anno)
        return anno

    def add_transcription(self, result, target, value, tag):
        """Add a describing Annotation."""
        anno = self._get_describing_annotation(result, target, value, tag)
        self._create_annotation(anno)
        return anno

    def add_tag(self, result, target, value, rect=None):
        """Add a tagging Annotation."""
        anno = self._get_tagging_annotation(result, target, value, rect)
        self._create_annotation(anno)
        return anno

    def _get_commenting_annotation(self, result, target, value, user):
        """Return a commenting Annotation."""
        anno = self._get_annotation_base(result, 'commenting')
        anno['target'] = target
        anno['body'] = {
            "type": "TextualBody",
            "value": value,
            "purpose": "commenting",
            "format": "text/plain"
        }
        if user:
            anno['creator'] = self._get_creator(user)
        return anno

    def _get_describing_annotation(self, result, target, value, tag):
        """Return a describing Annotation."""
        anno = self._get_annotation_base(result, 'describing')
        anno['target'] = target
        anno['body'] = [
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
        ]
        return anno

    def _get_tagging_annotation(self, result, target, value, rect):
        """Return a tagging Annotation."""
        anno = self._get_annotation_base(result, 'tagging')
        if rect:
            target = self._get_fragment_selector(target, rect)
        anno['target'] = target
        anno['body'] = {
            "type": "TextualBody",
            "purpose": "tagging",
            "value": value
        }
        return anno

    def _get_fragment_selector(self, target, rect):
        """Return a FragmentSelector."""
        return {
            'source': target,
            'selector': {
                'conformsTo': 'http://www.w3.org/TR/media-frags/',
                'type': 'FragmentSelector',
                'value': '?xywh={0},{1},{2},{3}'.format(rect['x'], rect['y'],
                                                        rect['w'], rect['h'])
            }
        }

    # def add_linking_body(self, anno, uri):
    #     """Add a link to a SpecificResource to the body of an Annotation."""
    #     link = {
    #         "purpose": "linking",
    #         "type": "SpecificResource",
    #         "source": uri
    #     }
    #     if not anno.get('body'):
    #         anno['body'] = link
    #     elif isinstance(anno['body'], list):
    #         anno['body'].append(link)
    #     elif isinstance(anno['body'], dict):
    #         anno['body'] = [
    #             anno['body'],
    #             link
    #         ]
    #     else:
    #         raise ValueError('Invalid Annotation body')

