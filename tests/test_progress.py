#!/usr/bin/env python
import unittest
from quicli.progress import *
from quicli.progress import unicode, unichr, get_columns, hide_cursor, show_cursor
import sys
from time import sleep

from tests import TextInterceptor

class ProgressTestCase(unittest.TestCase):
    def setUp(self):
        sys.stdout = TextInterceptor()
    def tearDown(self):
        sys.stdout = sys.__stdout__
    
class PercentageProgressTestCase(ProgressTestCase):
    def test_simple(self):
        with PercentageProgress(3) as progress:
            progress.update()
        self.assertIn('33%', sys.stdout.cache)
    
    def test_jump(self):
        with PercentageProgress(3) as progress:
            progress.update(2)
        self.assertIn('67%', sys.stdout.cache)
    
    def test_format(self):
        with PercentageProgress(3) as progress:
            progress.template = '{:.3%}'
            progress.update()
        self.assertIn('33.333%', sys.stdout.cache)
    
    def test_context(self):
        with PercentageProgress(3) as progress:
            progress.template += ' ({context})'
            progress.update(context='bagel')
        self.assertIn('33% (bagel)', sys.stdout.cache)

class TimeProgressTestCase(ProgressTestCase):
    def test_simple(self):
        with TimeProgress(1) as progress:
            sleep(.8)
        self.assertIn('0.5\x08\x08\x08', sys.stdout.cache)

class BarProgressTestCase(ProgressTestCase):
    def test_simple(self):
        with BarProgress(3) as progress:
            progress.update()
        bars = get_columns() // 3
        self.assertIn(unichr(0x2588) * bars, sys.stdout.cache)
