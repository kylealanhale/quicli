import unittest
from quicli import *
import sys
import inspect
import os
import imp

from tests import TextInterceptor

DEBUG = False

def get_scenario(name):
    sys.path.append('.')
    
    try:
        location = imp.find_module('scenarios')
        scenario = imp.load_module('scenarios', *location)
    finally:
        if location[0] is not None:
            location[0].close()
    
    try:
        location = imp.find_module(name, scenario.__path__)
        scenario = imp.load_module(name, *location)
    finally:
        if location[0] is not None:
            location[0].close()
    
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
    
    sys.stdout = stdout = TextInterceptor()
    sys.stderr = stderr = TextInterceptor()
    
    try:
        TEST_FUNCTION._quicli_assembler.run(True)
    except SystemExit:
        pass
    except:
        raise
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
    return (stdout.cache, stderr.cache)

POSITIONAL = 'positional arguments:'
OPTIONAL = 'optional arguments:'
def parse_arguments(stdout, stdin):
    lines = stdout.splitlines()
    
    if POSITIONAL in lines and lines.index(POSITIONAL) > 2:
        help = lines[2]
    elif POSITIONAL not in lines and OPTIONAL in lines and lines.index(OPTIONAL) > 2:
        help = lines[2]
    else:
        help = None
    
    if POSITIONAL in lines:
        positional = lines[lines.index(POSITIONAL) + 1:]
        positional = positional[:positional.index(OPTIONAL)]
    else:
        positional = None
        
    optional = lines[lines.index(OPTIONAL) + 1:]
    return {
        'help': help,
        'positional': ''.join([item.strip() for item in positional if item]) if positional is not None else None,
        'optional': ''.join([item.strip() for item in optional if item]) if optional is not None else None
    }

class SingleParserTestCase(unittest.TestCase):
    @scenario
    def test_simple(self):
        stdout, stderr = run_test('peace')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
    @scenario
    def test_simple_bad(self):
        stdout, stderr = run_test('peace --bad')
        self.assertIn('--bad', stderr)
        
    @scenario
    def test_simple_help(self):
        results = parse_arguments(*run_test('--help'))
        self.assertIn('help', results['help'])
        self.assertIn('arg1', results['positional'])
        
    @scenario
    def test_runlater(self):
        stdout, stderr = run_test('love')
        self.assertEqual('love is the answer\n', stdout)
        
    @scenario
    def test_runlater_nohelp(self):
        stdout, stderr = run_test('--help')
        self.assertIn('too few arguments', stderr)
        
    @scenario
    def test_optional(self):
        stdout, stderr = run_test('arg1 --kwarg1=thing')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
    @scenario
    def test_optional_help(self):
        results = parse_arguments(*run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('arg1', results['positional'])
        self.assertIn('--kwarg1 KWARG1, -k KWARG1', results['optional'])
        
    @scenario
    def test_modify(self):
        stdout, stderr = run_test('arg1 arg2 -t -r kwarg2')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
        stdout, stderr = run_test('arg1 arg2 --thing -r kwarg2')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
    
    @scenario
    def test_modify_bad(self):
        stdout, stderr = run_test('arg1 arg2 -t wrong')
        self.assertIn('wrong', stderr)
    
    @scenario
    def test_modify_help(self):
        results = parse_arguments(*run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('first argumentsecond_arg', results['positional'])  # Make sure the help is being displayed in the correct order
        self.assertIn('(default: False)', results['optional'])
        self.assertIn('-r KWARG2', results['optional'])
        
    @scenario
    def test_validate(self):
        stdout, stderr = run_test('crazy --file=__init__.py')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
        stdout, stderr = run_test('crazy -k __init__.py')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
        stdout, stderr = run_test('crazy --file=__init__.py --convert_to_int=3')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
    @scenario
    def test_validate_help(self):
        results = parse_arguments(*run_test('--help'))
        self.assertIsNone(results['help'])
        self.assertIn('--file FILE, -k FILE', results['optional'])
        self.assertIn("(default: ./test.txt)", results['optional'])

    @scenario
    def test_restart(self):
        stdout, stderr = run_test('initial')
        self.assertEqual('initial\nrestarted\n', stdout)
        
    def test_direct(self):
        # A directly-instantiated version of test_modify'''
        
        global TEST_FUNCTION
        
        scenario = get_scenario('direct')
        scenario.test_function._quicli_assembler = scenario.assembler
        TEST_FUNCTION = scenario.test_function
        stdout, stderr = run_test('arg1 arg2 --thing -r kwarg2')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
    def test_direct_help(self):
        global TEST_FUNCTION
        scenario = get_scenario('direct')
        scenario.test_function._quicli_assembler = scenario.assembler
        TEST_FUNCTION = scenario.test_function
        results = parse_arguments(*run_test('--help'))
        self.assertIn('arg1second_arg', results['positional'])  # Make sure the help is being displayed in the correct order
        
    def test_badargument1(self):
        with self.assertRaises(TypeError):
            get_scenario('badargument1')

    def test_badargument2(self):
        with self.assertRaises(TypeError):
            get_scenario('badargument2')
    
    @scenario
    def test_filechecks(self):
        filename = './__test.txt'
        if os.path.exists(filename):
            os.remove(filename)
        
        # Open
        stdout, stderr = run_test(filename)
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
        # Write
        with open(filename, 'r') as results:
            self.assertEqual('This test was a success!', results.read())
        
        # Open again
        stdout, stderr = run_test(filename)
        self.assertIn('"./__test.txt" is not a valid argument for some_file', stderr)
        
        # Cleanup
        os.remove(filename)

class SubParserTestCase(unittest.TestCase):
    @scenario
    def test_subparser(self):
        stdout, stderr = run_test('test_function value')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
        
        stdout, stderr = run_test('test_function3 value --elephant=yes')
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')
    
    @scenario
    def test_subparser_main_help(self):
        results = parse_arguments(*run_test('--help'))
        self.assertIn('Subparser main help', results['help'])
        self.assertIn('available subcommands (type " <subcommand> --help" for usage):', results['optional'])
        self.assertIn('Subparser sub-help', results['optional'])
        self.assertIn('This little piggie', results['optional'])

    @scenario
    def test_subparser_sub_help_1(self):
        results = parse_arguments(*run_test('test_function --help'))
        self.assertIn('Subparser sub-help', results['help'])
        self.assertIn('arg1', results['positional'])

    @scenario
    def test_subparser_sub_help_2(self):
        results = parse_arguments(*run_test('test_function2 --help'))
        self.assertIn('This little piggie', results['help'])
        self.assertIn('pig', results['positional'])

    @scenario
    def test_subparser_sub_help_3(self):
        results = parse_arguments(*run_test('test_function3 --help'))
        self.assertIn('--elephant', results['optional'])


def debug(*args):
    if DEBUG:
        sys.__stdout__.write('{}\n'.format(' '.join([str(arg) for arg in args])))
        sys.__stdout__.flush()
    
    return args[0] if len(args) == 1 else args
    
