# -*- coding: utf8 -*-
"""ResultCollection model."""

from flask import url_for

from .base import Base


class ResultCollection(Base):
    """ResultCollection model."""

    def __init__(self, iri):
        super(ResultCollection, self).__init__(iri)

    def add_comment(self, result, target, value, user=None):
        """Add a commenting Annotation."""
        self._validate(target=target, value=value)
        anno = self._get_commenting_annotation(result, target, value, user)
        anno = self._create_annotation(anno)
        return anno

    def add_transcription(self, result, target, value, tag):
        """Add a describing Annotation."""
        self._validate(target=target, value=value, tag=tag)
        anno = self._get_describing_annotation(result, target, value, tag)
        anno = self._create_annotation(anno)
        return anno

    def add_tag(self, result, target, value, rect=None):
        """Add a tagging Annotation."""
        self._validate(target=target, value=value)
        anno = self._get_tagging_annotation(result, target, value, rect)
        anno = self._create_annotation(anno)
        return anno

    def get_by_result(self, result):
        """Return current Annotations for a result."""
        contains = {
            'generator': [
                {
                    'id': url_for('api.api_result', oid=result.id),
                    'type': 'Software'
                }
            ]
        }
        return self._search_annotations(contains)

    def delete_batch(self, annotations):
        """Delete a batch of Annotations."""
        return self._delete_batch(annotations)

    def _validate(self, **kwargs):
        """Verify that the given values exist."""
        for k, v in kwargs.items():
            if not v or len(str(v)) < 1:
                err_msg = '"{}" is a required value'.format(k)
                raise ValueError(err_msg)

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

    def _get_linking_annotation(self, result, target, body):
        """Return a linking Annotation."""
        anno = self._get_annotation_base(result, 'linking')
        anno['target'] = target
        anno['body'] = body
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
