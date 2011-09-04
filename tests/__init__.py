import os
import sys
import unittest
import inspect

os.chdir(os.path.realpath(os.path.dirname(__file__)))
sys.path.append(os.path.realpath('..'))

tests = ('main', 'progress')

def load_tests(loader, standard_tests, pattern):
    sys.stdout.write('*' * 80 + '\n')
    sys.path.append('.')
    standard_tests.addTests(loader.loadTestsFromNames(['test_{}'.format(test) for test in tests]))
    sys.path.pop()
    return standard_tests

class TextInterceptor(object):
    def __init__(self):
        self.cache = ''
    def write(self, text):
        self.cache += text
    def flush(self, *args, **kwargs):
        pass

def mark(message='mark'):
    frame = inspect.currentframe().f_back
    file = frame.f_globals['__file__'].replace('.pyo', '.py').replace('.pyc', '.py')
    line = frame.f_lineno + 1
    sys.stdout.write('\nline {0} of {1}: {2}\n'.format(line, file, message))

if __name__ == '__main__':
    unittest.main()
