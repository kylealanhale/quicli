#!/usr/bin/env python

from quicli.guts import ParserAssembler

def test_function(arg1, arg2, kwarg1=False, kwarg2=None):
    pass

assembler = ParserAssembler(test_function, direct=True)
assembler.add_argument('arg1', 'arg1')
assembler.add_argument('arg2', 'second_arg')
assembler.add_argument('kwarg1', '--thing', '-t', default=False, action='store_true')
assembler.add_argument('kwarg2', '--kwarg2', '-r')
assembler.run()
