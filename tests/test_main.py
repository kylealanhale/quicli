import unittest
from quicli import *
import sys
import inspect
import os
import imp

from tests import TextInterceptor

def get_scenario(name):
    sys.path.append('.')
    location = imp.find_module('scenarios')
    scenario = imp.load_module('scenarios', *location)
    location = imp.find_module(name, scenario.__path__)
    scenario = imp.load_module(name, *location)
    sys.path.pop()
    
    return scenario

TEST_FUNCTION = None
def scenario(func):
    name = func.__name__.split('_')[1]
    def wrapper(self, *args, **kwargs):
        global TEST_FUNCTION
        scope = {}
        scenario = get_scenario(name)
        TEST_FUNCTION = scenario.test_function
        return func(self, *args, **kwargs)
        
    return wrapper

def run_test(command):
    sys.argv = [''] + command.split()
    interceptor = TextInterceptor()
    sys.stderr = interceptor
    sys.stdout = interceptor
    
    try:
        TEST_FUNCTION._quicli_assembler.run(True)
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
    def test_runlater(self):
        results = run_test('love')
        self.assertEqual(len(results), 1)
        
    @scenario
    def test_runlater_help(self):
        results = run_test('--help')
        self.assertIn('too few arguments', results[-1])
        
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
        self.assertIn('first argumentsecond_arg', results['positional'])  # Make sure the help is being displayed in the correct order
        self.assertIn('(default: False)', results['optional'])
        self.assertIn('-r KWARG2', results['optional'])
        
    @scenario
    def test_validate(self):
        results = run_test('crazy --file=__init__.py')
        self.assertEqual(len(results), 0)
        
        results = run_test('crazy -k __init__.py')
        self.assertEqual(len(results), 0)
        
        results = run_test('crazy --file=__init__.py --convert_to_int=3')
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
        
    def test_direct(self):
        '''A directly-instantiated version of test_modify'''
        
        global TEST_FUNCTION
        
        scenario = get_scenario('direct')
        scenario.test_function._quicli_assembler = scenario.assembler
        TEST_FUNCTION = scenario.test_function
        results = run_test('arg1 arg2 --thing -r kwarg2')
        self.assertEqual(len(results), 0)
        
    def test_direct_help(self):
        global TEST_FUNCTION
        scenario = get_scenario('direct')
        scenario.test_function._quicli_assembler = scenario.assembler
        TEST_FUNCTION = scenario.test_function
        results = parse_arguments(run_test('--help'))
        self.assertIn('arg1second_arg', results['positional'])  # Make sure the help is being displayed in the correct order
        
    def test_badargument1(self):
        with self.assertRaises(TypeError):
            get_scenario('badargument1')

    def test_badargument2(self):
        with self.assertRaises(TypeError):
            get_scenario('badargument2')

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

