#!/usr/bin/env python

from quicli import *

@run
@argument('some_file', type=FileType('a'), test=lambda file: not file.did_exist)
def test_function(some_file):
    some_file.write('This test was a success!')
