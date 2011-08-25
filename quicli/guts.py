#!/usr/bin/env python
import os
import inspect
from collections import OrderedDict
import argparse
from argparse import FileType as _OriginalFileType

class ParserAssembler(object):
    def __init__(self, func, *args, **kwargs):
        name = '__main__'
        self.subparsers = None
        self.__update_func_metadata(func if func else self.__get_script_global(), kwargs)
        self.parser = self.__generate_parser(argparse.ArgumentParser, func, name, args, kwargs)
        self.__add_func_args_to_parser(self.parser, func)
        
        self.__parsers = {name: self.parser}
        
        self.__was_imported = self.__get_script_global('__name__') != '__main__'
    
    def run(self, run_on_import=False):
        ''' Runs the program, at the entry point defined when the instance was created.
        
        bool run_on_import: By default, the program does not run if the calling module was imported.  Set this to True to override that behavior.
        '''
        if self.__was_imported and not run_on_import:  # Cancel running if the calling module was imported, unless it was explictly allowed to do so
            return
        
        # Parse arguments
        arguments = vars(self.parser.parse_args())
        parser_name = '__main__'
        if '_cl_parser' in arguments:
            parser_name = arguments['_cl_parser']
            del arguments['_cl_parser']
        parser = self.parser if parser_name == '__main__' else self.subparsers.choices[parser_name]
        instructions = parser._cl_instructions
        func = parser._cl_func
    
        # Check arguments
        kwargs = {}
        def test(value, suite):
            passed = True
            if value is not None and suite is not None:
                if not hasattr(suite, '__iter__'):
                    suite = [suite]
                for test in suite:
                    passed = passed and test(value)
            return passed
        for name, value in arguments.items():
            if name not in instructions:
                continue
            
            passed = False
            try:
                original_value = value
                if 'type' in instructions[name]:
                    value = instructions[name]['type'](value)
                if 'test' in instructions[name]:
                    passed = test(value, instructions[name]['test'])
            except:
                raise
            finally:
                if not passed:
                    parser.error(instructions[name]['error'].format(original_value, name, value=original_value, name=name))
            
            # Assign value to pass into function, substituting in the original name if it was modified earlier
            kwargs[instructions[name]['original_name'] if 'original_name' in instructions[name] else name] = value
        
        # Pass values to entry function
        def go():
            try:
                func(**kwargs)
            except RestartProgram as restarted:
                kwargs.update(restarted.kwargs)
                go()
        
        go()
    
    def add_argument(self, parser_name, argument_name, *args, **kwargs):
        parser = self.parser if parser_name == self.parser._cl_name else self.subparsers.choices[parser_name]
        if not hasattr(parser, '_cl_instructions'):
            parser._cl_instructions = {}
        parser._cl_instructions[argument_name] = self.__separate_instructions(kwargs)
        if 'default' in kwargs:
            message = '(default: {0})'.format(repr(kwargs['default']))
            if 'help' in kwargs:
                kwargs['help'] += os.linesep + message
            else:
                kwargs['help'] = message
        if 'type' in kwargs and kwargs['type'] == file:
            kwargs['type'] = FileType('r')
            if 'test' in kwargs:
                if not hasattr(kwargs['test'], '__iter__'):
                    kwargs['test'] = [kwargs['test']]
                kwargs['test'].append(lambda x: x is not None)
        parser.add_argument(*args, **kwargs)
    
    def add_subparser(self, func, *args, **kwargs):
        '''Adds a subcommand parser to the main parser'''
        # Create subparsers container
        if self.subparsers is None:
            title = 'available subcommands (type "{0} <subcommand> --help" for usage)'.format(self.parser.prog)
            self.subparsers = self.parser.add_subparsers(title=title, dest='_cl_parser')
            self.subparsers.choice = OrderedDict()
        
        # Make sure we have a name
        if not args:
            args = [func.__name__]
        
        # Set up validation cache
        name = args[0]
        if name.startswith('__'):
            raise ValueError('"{0}" cannot be used as a subcommand'.format(name))
        
        self.__update_func_metadata(func, kwargs)
        if 'description' in kwargs and 'help' not in kwargs:
            kwargs['help'] = kwargs['description']
        parser = self.__generate_parser(self.subparsers.add_parser, func, name, args, kwargs)
        self.__add_func_args_to_parser(parser, func)

    def __update_func_metadata(self, func, current):
        metadata = {'formatter_class': argparse.RawTextHelpFormatter}
        if func is not None:
            script_name = (func['__file__'] if isinstance(func, dict) else func.__globals__.get('__file__', 'program')).replace('.pyc', '.py').replace('.pyo', '.py')
            if script_name.endswith('__main__.py'):
                metadata['prog'] = os.path.basename(os.path.dirname(script_name))
            
            try:
                doc = (func['__doc__'] if isinstance(func, dict) else func.__doc__)
            except:
                doc = None
            if doc is not None:
                parts = doc.strip().split(os.linesep)
                metadata['description'] = parts[0]
                metadata['epilog'] = os.linesep.join(parts[1:]).strip()
            
        current.update(metadata)
    
    def __add_func_args_to_parser(self, parser, func):
        if func is None:
            return
        arguments = OrderedDict()
        argspecs = inspect.getargspec(func)
        defaults = list(argspecs.defaults) if argspecs.defaults is not None else []
        
        # Get argument cues from function signature
        for arg in reversed(argspecs.args):
            optional = False
            if defaults:
                default = defaults.pop()
                optional = True
            args = ['--' + arg, '-' + arg[0]] if optional else [arg]
            kwargs = {'default': default} if optional and default is not None else {}
            arguments[arg] = (args, kwargs)
            
        # Override generalizations made from above cues with specifications
        if hasattr(func, '_cl_arguments'):
            for override_args, override_kwargs in func._cl_arguments:
                if override_args and override_args[0] in arguments:  # Check for a name match
                    original_name = override_args[0]
                    new_name = None
                    args, kwargs = arguments[original_name]  # Get original cues
                    override_args = override_args[1:]  # Trim off matcher name
                    for index in range(len(args)):  # Iterate through all cue arguments
                        arg = args[index]
                        for override_arg in override_args:
                            if arg.startswith('--'):
                                if override_arg.startswith('--'):
                                    new_name = override_arg[2:]
                                    args[index] = override_arg
                            elif arg.startswith('-'):
                                if override_arg.startswith('-') and not override_arg.startswith('--'):
                                    args[index] = override_arg
                            else:
                                new_name = override_arg
                                args[:] = [override_arg]
                        if new_name is not None and not arg.startswith('-') or arg.startswith('--'):
                            # Store original name for later reference
                            override_kwargs['original_name'] = arg[2:] if arg.startswith('--') else arg
                    kwargs.update(override_kwargs)
                    if new_name is not None:
                        # Store as new name so that it will resolve properly later
                        arguments[new_name] = arguments[original_name]
                        del arguments[original_name]
        
        parser_name = parser._cl_name
        for name, (args, kwargs) in reversed(list(arguments.items())):
            self.add_argument(parser_name, name, *args, **kwargs)
    
    def __separate_instructions(self, kwargs):
        instructions = {
            'test': None,
            'error': None
        }
        default_error = '"{value}" is not a valid argument for {name}'
        
        if 'test' in kwargs:
            if hasattr(kwargs['test'], '__call__'):
                instructions['test'] = kwargs['test']
                instructions['error'] = default_error
            del kwargs['test']
        if 'original_name' in kwargs:
            instructions['original_name'] = kwargs['original_name']
            del kwargs['original_name']
        if 'type' in kwargs:
            if hasattr(kwargs['type'], '__call__'):
                instructions['type'] = kwargs['type']
                instructions['error'] = default_error
            del kwargs['type']
        if 'error' in kwargs:
            instructions['error'] = kwargs['error']
            del kwargs['error']
            
        return instructions
    
    def __get_script_global(self, *args, **kwargs):
        frame = inspect.currentframe()
        while hasattr(frame, 'f_back') and frame.f_back is not None:
            frame = frame.f_back
            if '__internal_frame' not in frame.f_locals and not ('self' in frame.f_locals and frame.f_locals['self'] == self):
                break
        if not args and not kwargs:
            return frame.f_globals
        return frame.f_globals.get(*args, **kwargs)

    def __generate_parser(self, factory, func, name, args, kwargs):
        parser = factory(*args, **kwargs)
        parser._cl_func = func
        parser._cl_name = name
        
        return parser

class FileType(_OriginalFileType):
    def __call__(self, *args, **kwargs):
        try:
            return super(FileType, self).__call__(*args, **kwargs)
        except:
            return None

class RestartProgram(Exception):
    def __init__(self, **kwargs):
        super(RestartProgram, self).__init__()
        self.kwargs = kwargs

def run_program(run_on_import=False, override_func=None):
    main_parser = [None, ([], {})]
    subparsers = []
    __internal_frame = True  # Used to detect the calling script
    
    def get_parser(obj):
        if hasattr(obj, '__call__'):
            if hasattr(obj, '_cl_subparser'):
                subparsers.append((obj, obj._cl_subparser))
            if hasattr(obj, '_cl_parser'):
                main_parser[0:] = [obj, obj._cl_parser]
        
    scope = inspect.currentframe().f_back.f_globals
    for name in scope:
        get_parser(scope[name])
    if override_func:
        get_parser(override_func)
    
    func, (args, kwargs) = main_parser
    assembler = ParserAssembler(func, *args, **kwargs)
    if func is not None:
        func._cl_assembler = assembler
    for func, (args, kwargs) in sorted(subparsers, key=lambda item: item[1][0][0] if item[1][0] else item[0].__name__):
        subparser = assembler.add_subparser(func, *args, **kwargs)
        func._cl_subparser_obj = subparser
        func._cl_assembler = assembler
    assembler.run(run_on_import)
    
    return assembler
