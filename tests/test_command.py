from __future__ import with_statement
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cu.command import Command  # CommandNotFound, ProcessExecutionError, ProcessTimedOut


class CommandTestCase(unittest.TestCase):
    def test_basic(self):
        t = Command('/bin/ls')
        self.assertEqual('/bin/ls', str(t))
        self.assertEqual('Command("/bin/ls")', repr(t))
