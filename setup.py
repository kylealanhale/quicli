#!/usr/bin/env python

from setuptools import setup, find_packages
import quicli
import sys

extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True
    
setup (
    name='quicli',
    version=quicli.__version__,
    description='quicli: write command line interfaces quickly',
    long_description='''
    A wrapper around Python's argparse module.  Provides argparse
    functionality in a simpler, easier-to-use interface, driven by function
    metadata and decorators, with data validation.
    
    For usage, visit http://dev.kylealanhale.com/wiki/projects/quicli
    ''',
    author='Kyle Alan Hale',
    author_email='kylealanhale@gmail.com',
    url='http://dev.kylealanhale.com/wiki/projects/quicli',
    license='BSD',
    keywords="command line cli",
    test_suite='tests',
    test_loader='unittest:TestLoader',
    packages=find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Environment :: Console'
    ],
    **extra
)
