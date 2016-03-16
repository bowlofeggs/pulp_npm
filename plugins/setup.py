#!/usr/bin/env python
from setuptools import find_packages, setup


setup(
    name='pulp_npm_plugins',
    version='0.0.1',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='plugins for npm support in pulp',
    entry_points={
        'pulp.importers': [
            'importer = pulp_npm.plugins.importers.importer:entry_point',
        ],
        'pulp.distributors': [
            'distributor = pulp_npm.plugins.distributors.web:entry_point'
        ]
    }
)
