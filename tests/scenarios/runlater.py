#!/usr/bin/env python

from quicli import *

@main(add_help=False)
def test_function(the_answer):
    '''This is help for test_function'''
    print('{} is the answer'.format(the_answer))

run()
