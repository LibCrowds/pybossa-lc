# -*- coding: utf8 -*-
"""Test projects API."""

from nose.tools import assert_equals
from helper import web
from default import with_context

from pybossa_lc.api import projects as projects_api


class TestProjectsApi(web.Helper):

    def setUp(self):
        super(TestProjectsApi, self).setUp()

    @with_context
    def test_get_valid_iiif_annotation_data(self):
        """Test the pattern for valid IIIF manifest URIs."""
        manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/manifest.json'
        volume = {
            'name': 'some_manifest',
            'source': manifest_uri
        }
        template = {'foo': 'bar'}
        data = projects_api._get_iiif_annotation_data(volume, template)
        expected = dict(type='iiif-annotation', manifest_uri=manifest_uri,
                        template=template)
        assert_equals(data, expected)

    @with_context
    def test_get_invalid_iiif_annotation_data(self):
        """Test the pattern for invalid IIIF manifest URIs."""
        manifest_uri = 'http://api.bl.uk/ark:/1/vdc_123/somethingelse'
        volume = {
            'name': 'some_manifest',
            'source': manifest_uri
        }
        template = {'foo': 'bar'}
        data = projects_api._get_iiif_annotation_data(volume, template)
        assert not data

    @with_context
    def test_get_valid_flickr_data(self):
        """Test the pattern for valid Flickr URIs."""
        album_id = '12345'
        base_url = 'http://www.flickr.com/photos/132066275@N04/albums/'
        album_uri = '{}{}'.format(base_url, album_id)
        volume = {
            'name': 'my_album',
            'source': album_uri
        }
        data = projects_api._get_flickr_data(volume)
        expected = dict(type='flickr', album_id=album_id)
        assert_equals(data, expected)

    @with_context
    def test_get_invalid_flickr_data(self):
        """Test the pattern for invalid Flickr URIs."""
        invalid_url = 'http://www.flickr.com/photos/132066275@N04'
        volume = {
            'name': 'my_album',
            'source': invalid_url
        }
        data = projects_api._get_flickr_data(volume)
        assert not data
