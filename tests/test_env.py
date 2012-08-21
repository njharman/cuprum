from __future__ import with_statement
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from cu import local, Path
from cu import CommandNotFound, ProcessExecutionError

from cu.env import Environment, SystemPathList


class EnvironmentTestCase(unittest.TestCase):
    def test_basic(self):
        t = Environment()
        list(t)  # __iter__
        self.assertRaises(TypeError, hash, t)
        len(t)
        self.assertTrue('PATH' in t)
        self.assertFalse('FOOBAR72' in t)
        self.assertRaises(KeyError, lambda: t['FOOBAR72'])
        self.assertRaises(ProcessExecutionError, local.python, '-c', 'import os;os.environ["FOOBAR72"]')
        t['FOOBAR72'] = 'spAm'
        self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR72"])').splitlines(), ['spAm'])
        del t['FOOBAR72']
        t.keys()
        t.items()
        t.values()
        t.get('HOME')
        #t.clear()
        #t.update()
        #t.as_dict()

    def test_contextmanager(self):
        t = Environment()
        with t(FOOBAR73=1889):
            self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1889'])
            with t(FOOBAR73=1778):
                self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1778'])
            self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1889'])
        self.assertRaises(ProcessExecutionError, local.python, '-c', 'import os;os.environ["FOOBAR73"]')

    def test_path(self):
        t = Environment()
        self.assertRaises(CommandNotFound, local.which, 'dummy-executable')
        self.assertTrue('foobar' != t['HOME'])
        with t():
            t['HOME'] = 'foobar'
            path = local.cwd / 'tests' / 'not-in-path'
            t.path.insert(0, path)
            self.assertEqual(path / 'dummy-executable', local.which('dummy-executable'))
        self.assertTrue('foobar' != t['HOME'])

    def test_expand(self):
        tests = (
                ('', ''),
                ('foo', 'foo'),
                ('foobutter', 'foo$CuPrUm_test'),
                ('foobutterb', 'foo${CuPrUm_test}b'),
                (os.environ['HOME'], '~'),
                )
        t = Environment()
        os.environ['CuPrUm_test'] = 'butter'
        for (expected, test) in tests:
            self.assertEqual(expected, t.expand(test))
        del os.environ['CuPrUm_test']


class SystemPathListTestCase(unittest.TestCase):
    def test_basic(self):
        env = dict(PATH='/bin:/usr/bin:')
        t = SystemPathList(env)
        self.assertEqual(2, len(t))
        self.assertEqual('/bin', t[0])
        self.assertEqual('/usr/bin', t[1])
        self.assertIsInstance(t[0], Path)
        self.assertTrue('/bin' in t)
        self.assertTrue(Path('/bin') in t)

    def test_changes(self):
        def checkit(length, path):
            self.assertEqual(length, len(t))
            self.assertEqual(path, env['PATH'])
        env = dict(PATH='/bin:/usr/bin:')
        t = SystemPathList(env)
        t.append('/sbin')
        checkit(3, '/bin:/usr/bin:/sbin')
        t.pop()
        checkit(2, '/bin:/usr/bin')
        t.extend(('/sbin/', '/usr/sbin'))
        checkit(4, '/bin:/usr/bin:/sbin:/usr/sbin')
        t[1] = '/'
        checkit(4, '/bin:/:/sbin:/usr/sbin')
        t.remove('/sbin/')
        checkit(3, '/bin:/:/usr/sbin')
