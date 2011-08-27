#!/usr/bin/env python

import os

from quicli import *

@run
@argument('arg1', test=lambda x: x == 'crazy')
@argument('kwarg1', '--file', test=os.path.exists)
def test_function(arg1, kwarg1='./test.txt'):
    pass
