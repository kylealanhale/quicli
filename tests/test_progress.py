#!/usr/bin/env python
import unittest
from quicli.progress import PercentageProgress
import sys

from tests import TextInterceptor

class PercentageProgressTestCase(unittest.TestCase):
    def setUp(self):
        sys.stdout = TextInterceptor()
    def tearDown(self):
        sys.stdout = sys.__stdout__
    
    def test_simple(self):
        progress = PercentageProgress(3)
        progress.update()
        self.assertEqual('33%', sys.stdout.cache)
    
    def test_jump(self):
        progress = PercentageProgress(3)
        progress.update(2)
        self.assertEqual('67%', sys.stdout.cache)
    
    def test_format(self):
        progress = PercentageProgress(3)
        progress.template = '{:.3%}'
        progress.update()
        self.assertEqual('33.333%', sys.stdout.cache)
    
    def test_context(self):
        progress = PercentageProgress(3)
        progress.template += ' ({context})'
        progress.update(context='bagel')
        self.assertEqual('33% (bagel)', sys.stdout.cache)
