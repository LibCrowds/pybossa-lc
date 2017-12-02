# -*- coding: utf8 -*-
"""Cache module."""

from pybossa.cache import delete_cached


def clear_cache():
    delete_cached('empty_results')
