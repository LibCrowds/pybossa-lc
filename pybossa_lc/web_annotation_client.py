# -*- coding: utf8 -*-
"""Web Annotation client module for pybossa-lc."""

import json
import requests


class WebAnnotationClient(object):

    def __init__(self, app=None):
        self.app = app
        if app is not None:  # pragma: no cover
            self.init_app(app)

    def init_app(self, app):
        """Configure the extension."""
        self.app = app
        self.base_url = app.config.get('WEB_ANNOTATION_BASE_URL')
        self.default_headers = app.config.get('WEB_ANNOTATION_HEADERS', {
            'Accept': ('application/ld+json; '
                       'profile="http://www.w3.org/ns/anno.jsonld"')
        })

    def get_collection(self, iri, minimal=False, iris=False):
        """Get an AnnotationCollection."""
        headers = {'Prefer': self._get_prefer_headers(minimal, iris)}
        response = requests.get(iri, headers=headers)
        response.raise_for_status()
        return response.json()

    def create_annotation(self, iri, annotation):
        """Add an Annotation."""
        response = requests.post(iri, data=json.dumps(annotation))
        response.raise_for_status()
        return response.json()

    def delete_batch(self, annotations):
        """Delete a batch of Annotations."""
        endpoint = self.base_url.rstrip('/') + '/batch/'
        response = requests.delete(endpoint, data=json.dumps(annotations))
        response.raise_for_status()

    def _get_prefer_headers(self, minimal=False, iris=False):
        """Return the Prefer header for given container preferences."""
        ns = ['http://www.w3.org/ns/oa#PreferContainedDescriptions']
        if iris:
            ns[0] = 'http://www.w3.org/ns/oa#PreferContainedIRIs'
        if minimal:
            ns.append('http://www.w3.org/ns/ldp#PreferMinimalContainer')
        return 'return=representation; include="{0}"'.format(' '.join(ns))

    def search_annotations(self, collectionIri, contains):
        """Search for Annotations with the given content."""
        collection_id = collectionIri.rstrip('/').split('/')[-1]
        endpoint = self.base_url.rstrip('/') + '/search/'
        params = {
            'collection.id': collection_id,
            'contains': contains
        }
        headers = {
            'Prefer': self._get_prefer_headers(minimal=True)
        }
        response = requests.get(endpoint, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data['total'] == 0:
            return []

        annotations = []

        def add_page_items(pageIri):
            r = requests.get(pageIri)
            if r.status_code == 404:  # pragma: no cover
                return
            elif r.status_code != 200:  # pragma: no cover
                r.raise_for_status()
            data = r.json()
            annotations.extend(data['items'])
            _next = data.get('next')
            if _next:
                add_page_items(_next)

        first = data['first']
        add_page_items(first)
        return annotations
