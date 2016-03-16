#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='pulp_npm_extensions_admin',
    version='0.0.1',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-admin extensions for npm package support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_npm.extensions.admin.pulp_cli:initialize',
        ]
    }
)
