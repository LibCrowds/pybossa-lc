# -*- coding: utf8 -*-
"""Web Annotation client module for pybossa-lc."""

import requests


class WebAnnotationClient(object):

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Configure the extension."""
        self.app = app
        self.base_url = app.config.get('WEB_ANNOTATION_BASE_URL')
        self.default_headers = app.config.get('WEB_ANNOTATION_HEADERS', {
            'Accept': ('application/ld+json; '
                       'profile="http://www.w3.org/ns/anno.jsonld"')
        })

    def get_collection(self, iri, page=None, minimal=False, iris=False):
        """Get an AnnotationCollection."""
        headers = {'Prefer': self._get_prefer_headers(minimal, iris)}
        params = {'page': page} if page else {}
        response = requests.get(iri, params=params, headers=headers)
        response.raise_for_status()
        return response.json

    def add_collection(self, iri, annotation):
        """Add an Annotation."""
        response = requests.post(iri, data=json.dumps(annotation))
        response.raise_for_status()
        return response.json

    def _get_prefer_headers(self, minimal, iris):
        """Return the Prefer header for given container preferences."""
        ns = ['http://www.w3.org/ns/oa#PreferContainedDescriptions']
        if iris:
            ns[0] = 'http://www.w3.org/ns/oa#PreferContainedIRIs'
        if minimal:
            ns.append('http://www.w3.org/ns/ldp#PreferMinimalContainer')
        return 'return=representation; include="{0}"'.format(' '.join(ns))
