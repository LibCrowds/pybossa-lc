# -*- coding: utf8 -*-
"""ResultCollection model."""

from flask import url_for

from .base import Base


class ResultCollection(Base):
    """ResultCollection model."""

    def __init__(self, iri):
        super(ResultCollection, self).__init__(iri)

    def add_comment(self, task, target, value, user=None):
        """Add a commenting Annotation."""
        self._validate_required_values(target=target, value=value)
        anno = self._get_commenting_annotation(task, target, value, user)
        anno = self._create_annotation(anno)
        return anno

    def add_transcription(self, task, target, value, tag):
        """Add a describing Annotation."""
        self._validate_required_values(target=target, value=value, tag=tag)
        anno = self._get_describing_annotation(task, target, value, tag)
        anno = self._create_annotation(anno)
        return anno

    def add_tag(self, task, target, value, rect=None):
        """Add a tagging Annotation."""
        self._validate_required_values(target=target, value=value)
        anno = self._get_tagging_annotation(task, target, value, rect)
        anno = self._create_annotation(anno)
        return anno

    def get_by_task(self, task):
        """Return current Annotations for a task."""
        contains = {
            'generator': [
                {
                    'id': url_for('api.api_task', oid=task.id),
                    'type': 'Software'
                }
            ]
        }
        return self._search_annotations(contains)

    def delete_batch(self, annotations):
        """Delete a batch of Annotations."""
        return self._delete_batch(annotations)

    def _validate_required_values(self, **kwargs):
        """Verify that the given values exist."""
        for k, v in kwargs.items():
            if not v or len(unicode(v)) < 1:
                err_msg = '"{}" is a required value'.format(k)
                raise ValueError(err_msg)

    def _get_annotation_base(self, task, motivation):
        """Return the base for a new Web Annotation."""
        base =  {
            "type": "Annotation",
            "motivation": motivation,
            "generator": self._get_generator(task)
        }
        if task.info and task.info.get('manifest'):
          base['partOf'] = task.info['manifest']
        return base

    def _get_commenting_annotation(self, task, target, value, user):
        """Return a commenting Annotation."""
        anno = self._get_annotation_base(task, 'commenting')
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

    def _get_describing_annotation(self, task, target, value, tag):
        """Return a describing Annotation."""
        anno = self._get_annotation_base(task, 'describing')
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

    def _get_tagging_annotation(self, task, target, value, rect):
        """Return a tagging Annotation."""
        anno = self._get_annotation_base(task, 'tagging')
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
