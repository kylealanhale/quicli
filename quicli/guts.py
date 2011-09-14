#!/usr/bin/env python
import os
import inspect
from collections import OrderedDict
import argparse
from argparse import FileType as _OriginalFileType

class ParserAssembler(object):
    def __init__(self, func, *args, **kwargs):
        name = '__main__'
        direct = False
        if 'direct' in kwargs:
            direct = kwargs['direct']
            del kwargs['direct']
        
        self.subparsers = None
        self.__update_func_metadata(func if func else _get_script_global(), kwargs)
        self.parser = self.__generate_parser(argparse.ArgumentParser, func, name, args, kwargs)
        
        if not direct:
            self.__add_func_args_to_parser(self.parser, func)
        
        self.__parsers = {name: self.parser}
        
        self.__was_imported = _get_script_global('__name__') != '__main__'
    
    def run(self, run_on_import=False):
        ''' Runs the program, at the entry point defined when the instance was created.
        
        bool run_on_import: By default, the program does not run if the calling module was imported.  Set this to True to override that behavior.
        '''
        if self.__was_imported and not run_on_import:  # Cancel running if the calling module was imported, unless it was explictly allowed to do so
            return
        
        # Parse arguments
        arguments = vars(self.parser.parse_args())
        parser_name = '__main__'
        if '_quicli_parser' in arguments:
            parser_name = arguments['_quicli_parser']
            del arguments['_quicli_parser']
        parser = self.parser if parser_name == '__main__' else self.subparsers.choices[parser_name]
        instructions = parser._quicli_instructions
        func = parser._quicli_func
    
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
        
        opened_files = []
        for name, value in arguments.items():
            if name not in instructions:
                continue
            
            passed = False
            try:
                original_value = value
                if 'type' in instructions[name]:
                    value = instructions[name]['type'](value)
                
                # Keep track of opened files so that we can make sure they are all closed later
                if isinstance(value, _file_wrapper):
                    opened_files.append(value)
                
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
        
        for file in opened_files:
            if not file.closed:
                file.close()
    
    def add_argument(self, argument_name, *args, **kwargs):
        original_name = argument_name
        
        # Look for argument renames
        for arg in args:
            if arg.startswith('--'):
                argument_name = arg[2:]
            elif not arg.startswith('-'):
                argument_name = arg
            
        if original_name != argument_name:
            kwargs['original_name'] = original_name
        
        # Find parser
        if 'parser_name' in kwargs:
            parser_name = kwargs['parser_name']
            del kwargs['parser_name']
        else:
            parser_name = '__main__'
        parser = self.parser if parser_name == self.parser._quicli_name else self.subparsers.choices[parser_name]
        
        # Get instructions
        if not hasattr(parser, '_quicli_instructions'):
            parser._quicli_instructions = {}
        parser._quicli_instructions[argument_name] = self.__separate_instructions(kwargs)
        if 'default' in kwargs:
            message = '(default: {0})'.format(str(kwargs['default']))
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
                
        # Add the argument to the parser
        parser.add_argument(*args, **kwargs)
    
    def add_subparser(self, func, *args, **kwargs):
        '''Adds a subcommand parser to the main parser'''
        # Create subparsers container
        if self.subparsers is None:
            title = 'available subcommands (type "{0} <subcommand> --help" for usage)'.format(self.parser.prog)
            self.subparsers = self.parser.add_subparsers(title=title, dest='_quicli_parser')
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

    @classmethod
    def _assemble(cls, run_on_import=False, _override_func=None):
        main_parser = [None, ([], {})]
        subparsers = []
        __internal_frame__ = True  # Used to detect the calling script
        
        def get_parser(obj):
            if hasattr(obj, '__call__'):
                if hasattr(obj, '_quicli_subparser'):
                    subparsers.append((obj, obj._quicli_subparser))
                elif hasattr(obj, '_quicli_parser'):
                    main_parser[0:] = [obj, obj._quicli_parser]
            
        scope = _get_script_global()
        
        for name in scope:
            get_parser(scope[name])
        if _override_func is not None:
                get_parser(_override_func)
            
        func, (args, kwargs) = main_parser
        assembler = ParserAssembler(func, *args, **kwargs)
        if func is not None:
            func._quicli_assembler = assembler
        for func, (args, kwargs) in sorted(subparsers, key=lambda item: item[1][0][0] if item[1][0] else item[0].__name__):
            subparser = assembler.add_subparser(func, *args, **kwargs)
            func._quicli_subparser_obj = subparser
            func._quicli_assembler = assembler
        assembler.run(run_on_import)
        
        return assembler
    
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
        '''Parses function defaults and overrides with internal instructions given by the decorators'''
        
        if func is None:
            return
        arguments = {}
        argspecs = inspect.getargspec(func)
        defaults = list(argspecs.defaults) if argspecs.defaults is not None else []
        
        # Get argument cues from function signature
        argument_order = []
        for arg in reversed(argspecs.args):
            argument_order[0:0] = [arg]
            optional = False
            if defaults:
                default = defaults.pop()
                optional = True
            args = ['--' + arg, '-' + arg[0]] if optional else [arg]
            kwargs = {'default': default} if optional and default is not None else {}
            arguments[arg] = (args, kwargs)            
            
        # Override generalizations made from above cues with specifications
        if hasattr(func, '_quicli_arguments'):
            for override_args, override_kwargs in func._quicli_arguments:
                argument_name = override_args[0]
                if override_args and argument_name in arguments:  # Check for a name match
                    args, kwargs = arguments[argument_name]  # Get original cues
                    override_args = override_args[1:]  # Trim off matcher name
                    
                    for index in range(len(args)):  # Iterate through all cue arguments
                        arg = args[index]
                        for override_arg in override_args:
                            if arg.startswith('--'):
                                if override_arg.startswith('--'):
                                    args[index] = override_arg
                            elif arg.startswith('-'):
                                if override_arg.startswith('-') and not override_arg.startswith('--'):
                                    args[index] = override_arg
                            else:
                                args[:] = [override_arg]
                    kwargs.update(override_kwargs)
        
        parser_name = parser._quicli_name
        for name in argument_order:
            args, kwargs = arguments[name]
            kwargs['parser_name'] = parser_name
            self.add_argument(name, *args, **kwargs)
    
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
    
    def __generate_parser(self, factory, func, name, args, kwargs):
        parser = factory(*args, **kwargs)
        parser._quicli_func = func
        parser._quicli_name = name
        
        return parser

class _file_wrapper(object):
    wrapped = None
    did_exist = False
    
    def __init__(self, wrapped, did_exist=None):
        self.__dict__['wrapped'] = wrapped
        if did_exist is not None:
            self.__dict__['did_exist'] = did_exist
    
    def __getattr__(self, name):
        return getattr(self.wrapped, name)
    def __setattr__(self, name, value):
        setattr(self.wrapped, name, value)
    def __delattr__(self, name):
        delattr(self.wrapped, name)

class FileType(_OriginalFileType):
    def __call__(self, filename):
        did_exist = os.path.exists(filename)
        try:
            file_object = super(FileType, self).__call__(filename)
            wrapped = _file_wrapper(file_object, did_exist)
        except Exception as e:
            wrapped = None
            
        return wrapped

class RestartProgram(Exception):
    def __init__(self, **kwargs):
        super(RestartProgram, self).__init__()
        self.kwargs = kwargs

def _get_script_global(*args, **kwargs):
    frame = inspect.currentframe()
    while hasattr(frame, 'f_back') and frame.f_back is not None:
        frame = frame.f_back
        if '__internal_frame__' not in frame.f_locals and not ('self' in frame.f_locals and isinstance(frame.f_locals['self'], ParserAssembler)):
            break
    if not args and not kwargs:
        return frame.f_globals
    return frame.f_globals.get(*args, **kwargs)

