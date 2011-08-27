#!/usr/bin/env python

import os

from quicli import *

@run
@argument('arg1', test=lambda x: x == 'crazy')
@argument('kwarg1', '--file', test=os.path.exists)
@argument('convert_to_int', type=int, test=lambda x: isinstance(x, int))
def test_function(arg1, kwarg1='./test.txt', convert_to_int=0):
    pass
