#!/usr/bin/env python

from quicli import *

count = 0
@run
def test_function(arg1):
    global count
    count += 1
    
    if count > 2:
        raise Exception('This program is trying to go on forever.')
        
    print(arg1)
    
    if arg1 != 'restarted':
        raise RestartProgram(arg1='restarted')
        
