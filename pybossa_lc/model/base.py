
# -*- coding: utf8 -*-
"""Base model."""

from flask import url_for, current_app

from .. import wa_client


class Base(object):
    """Base model.

    Works as a client for an AnnotationCollection stored on the server.
    """

    def __init__(self, iri):
        self.iri = iri
        self._check_iri()

    def _check_iri(self):
        """Check the Collection IRI is valid.

        The client should raise a requests.exceptions.HTTPError if not.
        """
        wa_client.get_collection(self.iri)

    def _get_annotation_base(self, result, motivation):
        """Return the base for a new Web Annotation."""
        return {
            "type": "Annotation",
            "motivation": motivation,
            "generator": self._get_generator(result)
        }

    def _get_generator(self, result):
        """Return a reference to the LibCrowds software."""
        spa_server_name = current_app.config.get('SPA_SERVER_NAME')
        github_repo = current_app.config.get('GITHUB_REPO')
        return [
            {
                "id": github_repo,
                "type": "Software",
                "name": "LibCrowds",
                "homepage": spa_server_name
            },
            {
                "id": url_for('api.api_result', oid=result.id),
                "type": "Software"
            }
        ]

    def _get_creator(self, user):
        """Return a reference to a LibCrowds user."""
        url = url_for('api.api_user', oid=user.id)
        return {
            "id": url,
            "type": "Person",
            "name": user.fullname,
            "nickname": user.name
        }

    def _create_annotation(self, anno):
        """Create an Annotation."""
        wa_client.create_annotation(self.iri, anno)  # pragma: no cover
