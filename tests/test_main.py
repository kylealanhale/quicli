import unittest
from quicli import *
import sys
import inspect
import os
import imp

from tests import TextInterceptor

TEST_FUNCTION = None
def scenario(func):
    name = func.__name__.split('_')[1]
    def wrapper(self, *args, **kwargs):
        global TEST_FUNCTION
        scope = {}
        sys.path.append('.')
        location = imp.find_module('scenarios')
        scenario = imp.load_module('scenarios', *location)
        location = imp.find_module(name, scenario.__path__)
        scenario = imp.load_module(name, *location)
        sys.path.pop()
        TEST_FUNCTION = scenario.test_function
        return func(self, *args, **kwargs)
        
    return wrapper

def run_test(command):
    sys.argv = [''] + command.split()
    interceptor = TextInterceptor()
    sys.stderr = interceptor
    sys.stdout = interceptor
    try:
        TEST_FUNCTION._cl_assembler.run(True)
    except SystemExit:
        pass
    except:
        raise
    finally:
        sys.stderr = sys.__stderr__
        sys.stdout = sys.__stdout__
        
    parts = interceptor.cache.strip().splitlines()
    return parts

POSITIONAL = 'positional arguments:'
OPTIONAL = 'optional arguments:'
def parse_arguments(results):
    if POSITIONAL in results and results.index(POSITIONAL) > 2:
        help = results[2]
    elif POSITIONAL not in results and OPTIONAL in results and results.index(OPTIONAL) > 2:
        help = results[2]
    else:
        help = None
    
    if POSITIONAL in results:
        positional = results[results.index(POSITIONAL) + 1:]
        positional = positional[:positional.index(OPTIONAL)]
    else:
        positional = None
        
    optional = results[results.index(OPTIONAL) + 1:]
    return {
        'help': help,
        'positional': ''.join([item.strip() for item in positional if item]) if positional is not None else None,
        'optional': ''.join([item.strip() for item in optional if item]) if optional is not None else None
    }

class SingleParserTestCase(unittest.TestCase):
    @scenario
    def test_simple(self):
        results = run_test('peace')
        self.assertEqual(len(results), 0)
        
    @scenario
    def test_simple_bad(self):
        results = run_test('peace --bad')
        self.assertIn('--bad', results[-1])
        
    @scenario
    def test_simple_help(self):
        results = parse_arguments(run_test('--help'))
        self.assertIn('help', results['help'])
        self.assertIn('arg1', results['positional'])
        
    @scenario
    def test_optional(self):
        results = run_test('arg1 --kwarg1=thing')
        self.assertEqual(len(results), 0)
        
    @scenario
    def test_optional_help(self):
        results = parse_arguments(run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('arg1', results['positional'])
        self.assertIn('--kwarg1 KWARG1, -k KWARG1', results['optional'])
        
    @scenario
    def test_modify(self):
        results = run_test('arg1 arg2 -t -r kwarg2')
        self.assertEqual(len(results), 0)
        results = run_test('arg1 arg2 --thing -r kwarg2')
        self.assertEqual(len(results), 0)
    
    @scenario
    def test_modify_bad(self):
        results = run_test('arg1 arg2 -t wrong')
        self.assertIn('wrong', results[-1])
    
    @scenario
    def test_modify_help(self):
        results = parse_arguments(run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('first argument', results['positional'])
        self.assertIn('second_arg', results['positional'])
        self.assertIn('(default: False)', results['optional'])
        self.assertIn('-r KWARG2', results['optional'])
        
    @scenario
    def test_validate(self):
        results = run_test('crazy --file=__init__.py')
        self.assertEqual(len(results), 0)
        
        results = run_test('crazy -k __init__.py')
        self.assertEqual(len(results), 0)
        
    @scenario
    def test_validate_help(self):
        results = parse_arguments(run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('--file FILE, -k FILE', results['optional'])
        self.assertIn("(default: './test.txt')", results['optional'])

    @scenario
    def test_restart(self):
        results = run_test('initial')
        self.assertEqual(len(results), 2)
        self.assertIn('restarted', results)

class SubParserTestCase(unittest.TestCase):
    @scenario
    def test_subparser(self):
        results = run_test('test_function value')
        self.assertEqual(len(results), 0)
        
        results = run_test('test_function3 value --elephant=yes')
        self.assertEqual(len(results), 0)
    
    @scenario
    def test_subparser_main_help(self):
        results = parse_arguments(run_test('--help'))
        self.assertIn('Subparser main help', results['help'])
        self.assertIn('available subcommands (type " <subcommand> --help" for usage):', results['optional'])
        self.assertIn('Subparser sub-help', results['optional'])
        self.assertIn('This little piggie', results['optional'])

    @scenario
    def test_subparser_sub_help_1(self):
        results = parse_arguments(run_test('test_function --help'))
        self.assertIn('Subparser sub-help', results['help'])
        self.assertIn('arg1', results['positional'])

    @scenario
    def test_subparser_sub_help_2(self):
        results = parse_arguments(run_test('test_function2 --help'))
        self.assertIn('This little piggie', results['help'])
        self.assertIn('pig', results['positional'])

    @scenario
    def test_subparser_sub_help_3(self):
        results = parse_arguments(run_test('test_function3 --help'))
        self.assertIn('--elephant', results['optional'])

