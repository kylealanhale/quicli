#!/usr/bin/env python
from . import run_program

def run(*args, **kwargs):
    run_on_import = False
    __internal_frame = True  # Used to detect the calling script
    generated_wrapper = None
    
    def wrapper():
        def wrapper(func):
            __internal_frame = True  # Used to detect the calling script
            setattr(func, '_cl_parser', (args, kwargs))
            run_program(run_on_import, func)
            return func
        return wrapper
    if len(args) == 1 and len(kwargs) == 0 and hasattr(args[0], '__call__'):
        func = args[0]
        args = list(args)[1:]
        generated_wrapper = wrapper()(func)
    else:
        if len(args):
            run_on_import = args[0]
        if 'run_on_import' in kwargs:
            run_on_import = kwargs['run_on_import']
        generated_wrapper = wrapper()
    
    return generated_wrapper

def sub(*args, **kwargs):
    def wrapper():
        def wrapper(func):
            setattr(func, '_cl_subparser', (args, kwargs))
            return func
        return wrapper
    if len(args) == 1 and len(kwargs) == 0 and hasattr(args[0], '__call__'):
        func = args[0]
        args = list(args)[1:]
        return wrapper()(func)
    else:
        return wrapper()

def argument(*args, **kwargs):
    def wrapper(func):
        if not hasattr(func, '_cl_arguments'):
            setattr(func, '_cl_arguments', [])
        func._cl_arguments.append((args, kwargs))
        return func
    return wrapper
