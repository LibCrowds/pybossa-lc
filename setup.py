# -*- coding: utf8 -*-
"""
pybossa-lc
-------------
A PYBOSSA plugin for managing LibCrowds projects.
"""

import os
import json
from setuptools import setup


HERE = os.path.dirname(__file__)
INFO = os.path.join(HERE, 'pybossa_lc', 'info.json')
VERSION = json.load(open(INFO))['version']
LONG_DESCRIPTION = open(os.path.join(HERE, 'README.md')).read()


setup(
    name="pybossa-lc",
    version=VERSION,
    author="Alexander Mendes",
    author_email="alexanderhmendes@gmail.com",
    description="A PYBOSSA plugin for managing LibCrowds projects.",
    license="MIT",
    url="https://github.com/LibCrowds/pybossa-lc",
    packages=['pybossa_lc'],
    long_description=LONG_DESCRIPTION,
    zip_safe=False,
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
)
