#!/usr/bin/env python
'''Subparser main help'''

from quicli import *

@sub
def test_function(arg1):
    '''Subparser sub-help'''
    pass

@sub(description='This little piggie')
@argument('arg1', 'pig')
def test_function2(arg1):
    pass

@sub
@argument('kwarg1', '--elephant', '-e')
def test_function3(arg1, kwarg1=None):
    pass

run_program()
