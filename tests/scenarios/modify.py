#!/usr/bin/env python

from quicli import *

@run
@argument('arg1', help='first argument')
@argument('arg2', 'second_arg')
@argument('kwarg1', '--thing', '-t', action='store_true')
@argument('kwarg2', '-r')
def test_function(arg1, arg2, kwarg1=False, kwarg2=None):
    pass
