from __future__ import with_statement
import os
import unittest
#from cu import local, Path, FG, BG, ERROUT
#from cu import CommandNotFound, ProcessExecutionError, ProcessTimedOut
from cu import Path

# NOTE: all tests assume *unix OS.


class PathTestCase(unittest.TestCase):
    def test_construction(self):
        # normpath'd except empty paths and trailing slashes are preserved
        tests = (
            ('', ''),
            ('/', '/'),
            ('/../', '/'),
            ('foo.txt', 'foo.txt'),
            ('some/path////', 'some/path/'),
            ('/some/abs/path/', '/some/abs/path/'),
            ('full/path/foo.txt', 'full/path/foo.txt'),
            ('normalize/../me/prleaze.txt', 'me/prleaze.txt'),
            (Path('from/Path'), 'from/Path'),
            )
        for test, expected in tests:
            t = Path(test)
            self.assertEqual(expected, t)
        t = Path('from', 'bits')
        self.assertEqual('from/bits', t)

    def test_no_trailing_slash(self):
        tests = (
            ('', ''),
            ('/', '/'),
            ('/../', '/'),
            ('foo.txt', 'foo.txt'),
            ('some/path////', 'some/path'),
            ('/some/abs/path/', '/some/abs/path'),
            ('full/path/foo.txt', 'full/path/foo.txt'),
            ('normalize/../me/prleaze.txt', 'me/prleaze.txt'),
            )
        for test, expected in tests:
            t = Path(test, keep_trailing_slash=False)
            self.assertEqual(expected, t)
        t = Path('from', 'bits/', keep_trailing_slash=False)
        self.assertEqual('from/bits', t)
        t = Path('from', 'bits/', keep_trailing_slash=False)
        self.assertEqual('from/bits/trail', t.join('trail/'))

    def test_string_methods(self):
        t = Path('/some/path/file.txt')
        self.assertTrue(t.endswith('txt'))
        self.assertIsInstance(t.rstrip('.'), Path)
        self.assertIsInstance(t.split('.')[0], Path)
        self.assertIsInstance(t.rfind('.'), int)
        self.assertIsInstance(t.rfind('.'), int)
        self.assertIsInstance(t.islower(), bool)

    def test_string_indexing(self):
        t = Path('/some/path/file.txt')
        self.assertEqual('/so', t[:3])
        self.assertIsInstance(t[:3], Path)

    def test_equality(self):
        class FooBar:
            def __str__(self):
                return '/foo/bar'
        equal = (
                (Path(''), Path('')),
                (Path(''), ''),
                (Path('/foo/bar'), Path('/foo/bar')),
                (Path('/foo/bar'), u'/foo/bar'),
                (Path('/foo/bar'), FooBar()),
                )
        notequal = (
                (Path('/foo/bar'), Path('/foo/bar/')),
                (Path('/foo/bar'), u'/foo/bar/'),
                (Path('crazy'), FooBar()),
                (Path('crazy'), 'sause'),
                (Path('crazy'), True),
                )
        for a, b in equal:
            self.assertEqual(a, b)
            self.assertEqual(b, a)
        for a, b in notequal:
            self.assertNotEqual(a, b)
            self.assertNotEqual(b, a)

    def test_hash(self):
        path = '/foo/bar'
        t = Path(path)
        self.assertEqual(hash(t), hash(Path(path)))
        self.assertEqual(hash(t), hash(path))

    def test_nonzero(self):
        self.assertTrue(Path(' '))
        self.assertTrue(Path('/adf'))
        self.assertFalse(Path(''))

    def test_basename(self):
        tests = (
            ('', ''),
            ('/', ''),
            ('file.txt', 'file.txt'),
            ('/file.txt', 'file.txt'),
            ('/path/to/file.txt', 'file.txt'),
            ('path/', ''),  # different than unix basename
            ('/path/trailing', 'trailing'),
            ('/stupid/path/with.dots/wazzup?', 'wazzup?'),
            ('/stupid/path/with spaces', 'with spaces'),
            )
        for test, expected in tests:
            t = Path(test)
            self.assertIsInstance(t.basename, basestring)
            self.assertEqual(expected, t.basename, test)

    def test_dirname(self):
        tests = (
            ('', ''),
            ('/', '/'),
            ('file.txt', ''),
            ('/path/to/file.txt', '/path/to'),
            ('path/', 'path'),
            ('/path/trailing', '/path'),
            ('/stupid/path/with.dots/wazzup?', '/stupid/path/with.dots'),
            ('/path/with spaces/yo', '/path/with spaces'),
            )
        for test, expected in tests:
            t = Path(test)
            self.assertIsInstance(t.dirname, Path)
            self.assertEqual(expected, t.dirname)

    # requires being run as root
    def ftest_group_owner_chown(self):
        PATH = '/tmp/delme.txt'
        path = Path(PATH)
        os.system('rm %s' % PATH)
        os.system('touch %s' % PATH)
        self.assertTrue('nobody' != path.owner)
        self.assertTrue('nogroup' != path.group)
        # chown group
        path.chown(group='nogroup')
        self.assertEqual('nogroup', path.group)
        self.assertTrue('nobody' != path.owner)
        # chown owner
        path.chown('nobody')
        self.assertEqual('nobody', path.owner)
        # chown both / numerical ids
        path.chown(uid=0, gid=0)
        self.assertEqual('root', path.owner)
        self.assertEqual('root', path.group)
        # recursive
        path.chown('root', recursive=True)
        # set properties
        path.owner = 'nobody'
        self.assertEqual('nobody', path.owner)
        path.group = 'nogroup'
        self.assertEqual('nogroup', path.group)
        path.delete()

    def test_isfile(self):
        t = Path('/tmp')
        self.assertFalse(t.isfile())
        t = Path('/etc/passwd')
        self.assertTrue(t.isfile())

    def test_isdir(self):
        t = Path('/tmp')
        self.assertTrue(t.isdir())
        t = Path('/etc/passwd')
        self.assertFalse(t.isdir())

    def test_exists(self):
        t = Path('/tmp')
        self.assertTrue(t.exists())
        t = Path('/etc/passwd')
        self.assertTrue(t.exists())
        t = Path('/I/like/oatmeal/cookies')
        self.assertFalse(t.exists())

    def test_stat(self):
        t = Path('/tmp')
        self.assertTrue(t.stat())

    def test_join(self):
        tests = (
            (('', ''), ''),
            (('/', ''), '/'),
            (('', '/4', '/me/'), '/4/me/'),
            (('', 'yo', 'como'), 'yo/como'),
            ((Path(''), '', '/4', Path(''), '/me/', ''), '/4/me/'),
            (('', Path(''), 'yo', '', '', 'como'), 'yo/como'),
            (('/', '../', '../'), '/'),
            (('file.txt', ''), 'file.txt'),
            (('', 'file.txt', ''), 'file.txt'),
            (('/path/', 'to', '/file.txt', ), '/path/to/file.txt'),
            (('trailing/', Path('slash'), '/preserved/', ), 'trailing/slash/preserved/'),
            (('path/', '../to', '/file.txt', ), 'to/file.txt'),
            (('path/', '../to', '..//file.txt', ), 'file.txt'),
            (('stupid/', '/path/', '/with.dots/', '/wazzup?', ), 'stupid/path/with.dots/wazzup?'),
            ((Path('path/'), Path('with spaces '), ' ', Path('yo/'), ), 'path/with spaces / /yo/'),
            )
        for bits, expected in tests:
            t = Path(bits[0]).join(*bits[1:])
            self.assertEqual(expected, t)
        # test div operator which calls self.join
        t = Path('/foo/bar')
        self.assertEqual('/foo/car', t / '../car')

    def test_glob(self):
        t = Path('/foo/bar')
        self.assertEqual([], t.glob('*'))

    def test_up(self):
        self.assertEqual('/foo/', Path('/foo/bar').up())
        self.assertEqual('/', Path('/foo/bar').up(2))
        self.assertEqual('/', Path('/foo/bar').up(8))

    def test_walk(self):
        t = Path('/etc/passwd')
        for f in t.walk():
            pass

    def test_list(self):
        t = Path('/tmp')
        t.list()

    def test_chdir(self):
        self.assertTrue('/tmp' != os.getcwd())
        curdir = os.getcwd()
        t = Path('/tmp')
        t.chdir()
        self.assertEqual('/tmp', os.getcwd())
        os.chdir(curdir)
