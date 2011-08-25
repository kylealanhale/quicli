'''
    quicli: write command line interfaces quickly
    
    A wrapper around Python's argparse module.  Provides argparse
    functionality in a simpler, easier-to-use interface, driven by function
    metadata and decorators, with data validation.
    
    For usage, visit http://dev.kylealanhale.com/wiki/projects/quicli
'''

from .guts import *
from .decorators import *

__all__ = ('run', 'run_program', 'sub', 'argument', 'FileType', 'RestartProgram')
__version__ = '1.0.0'
