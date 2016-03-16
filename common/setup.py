#!/usr/bin/env python
from setuptools import find_packages, setup


setup(
    name='pulp_npm_common',
    version='0.0.1',
    packages=find_packages(),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='Common code for Pulp\'s npm support.',
)
