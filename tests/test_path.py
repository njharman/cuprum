from __future__ import with_statement
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import sys
import pwd
import grp
import tempfile

import six

from cu import Path


# NOTE: All tests currently assume a *unix environment.


def tmpfile(delete=False):
    # Python 2.5 NamedTemporaryFile does not support delete arg
    # TODO: Python 2.5 compatible verson
    return tempfile.NamedTemporaryFile(delete=delete, prefix='cuprum_test_')


class PathTestCase(unittest.TestCase):
    longMessage = True

    def test_some_imports(self):
        from cu.path import commonprefix, sameopenfile, samestat
        for f in commonprefix, sameopenfile, samestat:
            self.assertTrue(six.callable(f))

    def test_construction(self):
        # normpath'd except empty paths and trailing slashes are preserved
        tests = (
            ('', ''),
            ('.', '.'),
            ('..', '..'),
            ('/', '/'),
            ('/..', '/'),
            ('/../', '/'),
            ('../', '../'),
            ('path/..', ''),
            ('path/../', ''),
            ('path/../../', '../'),
            ('foo.txt', 'foo.txt'),
            ('some/path////', 'some/path/'),
            ('/some/abs/path/', '/some/abs/path/'),
            ('full/path/foo.txt', 'full/path/foo.txt'),
            ('normalize/../me/prleaze.txt', 'me/prleaze.txt'),
            ('normalize/../me/', 'me/'),
            (Path('from/Path'), 'from/Path'),
            )
        for test, expected in tests:
            t = Path(test)
            self.assertEqual(expected, t, test)
        t = Path('from', 'bits')
        self.assertEqual('from/bits', t)

    def test_no_trailing_slash_construction(self):
        tests = (
            ('', ''),
            ('.', '.'),
            ('..', '..'),
            ('/', '/'),
            ('/..', '/'),
            ('/../', '/'),
            ('../', '..'),
            ('path/..', ''),
            ('path/../', ''),
            ('path/../../', '..'),
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

    def test_common_prefix_construction(self):
        tests = (
            ((), ''),
            (('', ''), ''),
            (('/', '/var'), '/'),
            (('var', 'var'), 'var'),
            (('var', 'var/'), 'var'),
            (('/var', '/var'), '/var'),
            (('/var', '/var/'), '/var'),
            (('/var/', '/var/'), '/var'),
            (('/var', 'var'), ''),
            (('/var', '/varible'), '/'),
            (('/var/log', 'var/log'), ''),
            (('/var/log/', '/var/log/kernel'), '/var/log'),
            (('/var/log', '/var/logged', '/var/log/kernel'), '/var'),
            )
        for test, expected in tests:
            result = Path.common_prefix(test)
            self.assertEqual(expected, result)
            self.assertIsInstance(result, Path)
            if expected:
                self.assertEqual(expected, Path.common_prefix(*test))

    def test_common_suffix_construction(self):
        tests = (
            ((), ''),
            (('', ''), ''),
            (('/', '/'), '/'),
            (('var', 'var'), 'var'),
            (('var', '/var'), 'var'),
            (('/var', '/var'), '/var'),
            (('/var', '/var/'), '/var'),
            (('/var/', '/var/'), '/var/'),
            (('bar/log', '/var/log'), '/log'),
            (('/some/longible', '/varible'), ''),
            (('/var/log', 'bar/logged'), ''),
            (('/kernel/log', '/sys/log', '/lady/log'), '/log'),
            )
        for test, expected in tests:
            result = Path.common_suffix(test)
            self.assertIsInstance(result, Path, test)
            self.assertEqual(expected, result, test)
            if expected:
                self.assertEqual(expected, Path.common_suffix(*test), test)

    def test_cwd_construction(self):
        self.assertIsInstance(Path.cwd(), Path)
        self.assertIsInstance(Path.getcwd(), Path)

    def test_string_methods(self):
        t = Path('/some/path/file.txt')
        self.assertTrue(t.endswith('txt'))
        self.assertIsInstance(t.rstrip('.'), Path)
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
                (Path('/foo/bar'), six.u('/foo/bar')),
                (Path('/foo/bar'), FooBar()),
                )
        notequal = (
                (Path('/foo/bar'), Path('/foo/bar/')),
                (Path('/foo/bar'), six.u('/foo/bar/')),
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

    def test_abs(self):
        tests = (
            ('', ''),
            ('.', os.getcwd()),
            ('/', '/'),
            ('./file.txt', os.getcwd() + '/file.txt'),
            ('file.txt', os.getcwd() + '/file.txt'),
            ('/../../file.txt', '/file.txt'),
            ('/path/to/some/place', '/path/to/some/place'),
            ('/path/../place/', '/place/'),
            ('/path/to/some/../../foo/place/', '/path/foo/place/'),
            )
        for test, expected in tests:
            t = Path(test).abs
            self.assertIsInstance(t, Path)
            self.assertEqual(expected, t, test)

    def test_basename(self):
        tests = (
            ('', ''),
            ('/', ''),
            ('file.txt', 'file.txt'),
            ('/file.txt', 'file.txt'),
            ('file.txt/', ''),
            ('/path/to/file.txt', 'file.txt'),
            ('path/', ''),  # different than unix basename
            ('/path/trailing', 'trailing'),
            ('/stupid/path/with.dots/wazzup?', 'wazzup?'),
            ('/stupid/path/with spaces', 'with spaces'),
            )
        for test, expected in tests:
            t = Path(test).basename
            self.assertIsInstance(t, Path, test)
            self.assertEqual(expected, t, test)

    def test_name(self):
        tests = (
            ('', ''),
            ('/', ''),
            ('file.txt/', ''),
            ('file.txt', 'file'),
            ('/file.txt', 'file'),
            ('/file.', 'file'),
            ('/file-1.0.3.txt', 'file-1.0.3'),
            ('/.secrets', '.secrets'),
            (' .edgecase_ftw', ' '),
            ('/file.tar.gz', 'file.tar'),
            ('/path/to/file.txt', 'file'),
            ('/path/no_ext', 'no_ext'),
            ('/stupid/path/with.dots/wazzup?', 'wazzup?'),
            ('/stupid/path/with spaces.foo', 'with spaces'),
            )
        for test, expected in tests:
            t = Path(test).name
            self.assertIsInstance(t, Path, test)
            self.assertEqual(expected, t, test)

    def test_extension(self):
        tests = (
            ('', ''),
            ('/', ''),
            ('file.txt/', ''),
            ('file.txt', '.txt'),
            ('/file.txt', '.txt'),
            ('/file.', '.'),
            ('/file-1.0.3.txt', '.txt'),
            ('/.secrets', ''),
            (' . edgecase_ftw', '. edgecase_ftw'),
            ('/file.tar.gz', '.gz'),
            ('/path/to/file.txt', '.txt'),
            ('/path/no_ext', ''),
            ('/stupid/path/with.dots/wazzup?', ''),
            ('/stupid/path/foo.with spaces', '.with spaces'),
            )
        for test, expected in tests:
            t = Path(test).extension
            self.assertIsInstance(t, six.string_types, test)
            self.assertEqual(expected, t, test)

    def test_dirname(self):
        tests = (
            ('', ''),
            ('/', '/'),
            ('var', ''),
            ('var/', 'var/'),
            ('var/log', 'var/'),
            ('/some', '/'),
            ('/some/', '/some/'),
            ('/some/dir/', '/some/dir/'),
            ('/some/file.txt', '/some/'),
            ('file.txt', ''),
            ('/path/to/file.txt', '/path/to/'),
            ('path/', 'path/'),
            ('/path/trailing', '/path/'),
            ('/stupid/path/with.dots/wazzup?', '/stupid/path/with.dots/'),
            ('/path/with spaces/yo', '/path/with spaces/'),
            )
        for test, expected in tests:
            t = Path(test).dirname
            self.assertIsInstance(t, Path)
            self.assertEqual(expected, t, test)

    def test_parent(self):
        tests = (
            ('', ''),
            ('/', '/'),
            ('var', ''),
            ('var/', ''),
            ('var/log', 'var/'),
            ('/some', '/'),
            ('/some/', '/'),
            ('/some/dir/', '/some/'),
            ('/some/file.txt', '/some/'),
            ('file.txt', ''),
            ('/path/to/file.txt', '/path/to/'),
            ('path/', ''),
            ('/path/trailing', '/path/'),
            ('/stupid/path/with.dots/wazzup?', '/stupid/path/with.dots/'),
            ('/path/with spaces/yo', '/path/with spaces/'),
            )
        for test, expected in tests:
            t = Path(test).parent
            self.assertIsInstance(t, Path)
            self.assertEqual(expected, t, test)

    def test_up(self):
        tests = (
            ('', ''),
            ('/', '/'),
            ('var', ''),
            ('var/', ''),
            ('var/log', 'var/'),
            ('/some', '/'),
            ('/some/', '/'),
            ('/some/dir/', '/some/'),
            ('/some/file.txt', '/some/'),
            ('file.txt', ''),
            ('/path/to/file.txt', '/path/to/'),
            ('path/', ''),
            ('/path/trailing', '/path/'),
            ('/stupid/path/with.dots/wazzup?', '/stupid/path/with.dots/'),
            ('/path/with spaces/yo', '/path/with spaces/'),
                )
        for test, expected in tests:
            t = Path(test).up()
            self.assertIsInstance(t, Path)
            self.assertEqual(expected, t, test)
        self.assertEqual('/', Path('/foo/bar').up(2))
        self.assertEqual('', Path('foo/bar').up(8))
        self.assertIsInstance(Path('/').up(8), Path)

    def test_exists(self):
        t = Path('/tmp')
        self.assertTrue(t.exists)
        t = Path('/etc/passwd')
        self.assertTrue(t.exists)
        t = Path('/I/like/oatmeal/cookies')
        self.assertFalse(t.exists)

    def test_isabs(self):
        abs = (
            '/tmp',
            )
        relative = (
            'tmp',
            './tmp',
            '../tmp',
                )
        for path in abs:
            t = Path(path)
            self.assertTrue(t.is_abs)
            self.assertFalse(t.is_relative)
        for path in relative:
            t = Path(path)
            self.assertFalse(t.is_absolute)
            self.assertTrue(t.is_relative)

    def test_isdir(self):
        self.assertTrue(Path('/tmp').isdir)
        self.assertFalse(Path('/etc/passwd').isdir)

    def test_isfile(self):
        self.assertFalse(Path('/tmp').isfile)
        self.assertTrue(Path('/etc/passwd').isfile)

    def test_islink(self):
        self.assertFalse(Path('/tmp').islink)
        self.assertFalse(Path('/etc/passwd').islink)
        #TODO: test actual link

    def test_ismount(self):
        self.assertTrue(Path('/proc').ismount)
        self.assertFalse(Path('/etc/passwd').ismount)

    def test_times(self):
        t = Path('/tmp')
        t.atime
        t.mtime
        t.ctime

    def test_size(self):
        Path('/tmp').size
        Path('/etc/passwd').size

    @unittest.skipIf(sys.version.startswith('2.5'), 'Unsupported for Python 2.5 (see tmpfile)')
    def test_group_owner(self):
        self.assertEqual('root', Path('/tmp').owner)
        self.assertEqual('root', Path('/etc/passwd').group)
        fh = tmpfile()
        try:
            t = Path(fh.name)
            # these aren't actually changing anything (need to be root for that)
            # but they do at least exercise the code
            t.owner = pwd.getpwuid(os.getuid()).pw_name
            t.group = grp.getgrgid(os.getgid()).gr_name
            t.owner = '%s:%s' % (t.owner, t.group)
            t.chown(t.owner)
            t.chown(t.owner, t.group)
            t.chown('%s:%s' % (t.owner, t.group), recursive=True)
        finally:
            os.remove(fh.name)

    @unittest.skipIf(sys.version.startswith('2.5'), 'Unsupported for Python 2.5 (see tmpfile)')
    def test_mode(self):
        #self.assertEqual('root', Path('/etc/passwd').mode)
        #self.assertEqual('root', Path('/tmp').mode)
        fh = tmpfile()
        try:
            t = Path(fh.name)
            t.mode = 644
            t.chmod(666)
            t.chmod('u+x')
            t.chmod('0777', recursive=True)
        finally:
            os.remove(fh.name)

    @unittest.skip('TODO: changing owner/group requires root.')
    def test_group_owner_chown(self):
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

    def test_stat(self):
        t = Path('/tmp')
        t.stat()
        t.stat(followlinks=False)  # TODO: test actual symlink
        t.statfs()
        t.statvfs()

    def test_split(self):
        # testing that Python's string.split works, just that os.sep is default
        # rather than whitespace.
        tests = (
            ('', []),
            ('  ', ['  ', ]),
            ('/', ['/', ]),
            (' /', [' ', ]),
            (' /  ', [' ', '  ']),
            ('/var', ['/', 'var']),
            ('var', ['var', ]),
            ('var/', ['var', ]),
            ('var/foo', ['var', 'foo']),
            ('/some/ path/ /awesome.txt', ['/', 'some', ' path', ' ', 'awesome.txt']),
            # remember these are normalized Path
            #('../', ['..', ]),
            #('/..', ['/', '..', ]),
            #('/var/../', ['/', 'var', '..', ]),
            #('/..var/..', ['/', '..var', '..']),
            ('//', ['/', ]),
            ('/var//log/', ['/', 'var', 'log']),
            ('//var//log/', ['/', 'var', 'log']),
            (r'\wrong\way', ['\wrong\way', ]),
            )
        for test, expected in tests:
            result = Path(test).split()
            for p in result:
                self.assertIsInstance(p, Path, test)
            self.assertSequenceEqual(expected, result, test)
        # non os.sep split
        self.assertSequenceEqual(('/var', 'd', '/bar'), Path('/var%d%/bar').split('%'))
        # TODO: rsplit, maxsplit

    def test_split_path(self):
        tests = (
            '',
            '  ',
            '/',
            ' /',
            ' /  ',
            '/var',
            'var',
            'var/',
            'var/foo',
            '/some/ path/ /awesome.txt',
            )
        for test in tests:
            result = Path(test).split_path()
            expected = os.path.split(test)
            for p in result:
                self.assertIsInstance(p, Path, test)
            self.assertSequenceEqual(expected, result, test)

    def test_split_drive(self):
        tests = (
            (''),
            ('/'),
            ('/bob'),
            ('c:/bob'),
            (r'c:\bob'),
            )
        for test in tests:
            result = Path(test).split_drive()
            expected = os.path.splitdrive(test)
            for p in result:
                self.assertIsInstance(p, Path, test)
            self.assertSequenceEqual(expected, result, test)

    def test_split_extension(self):
        tests = (
            '',
            '/',
            'file.txt/',
            'file.txt',
            '/file.txt',
            '/file.',
            '/file-1.0.3.txt',
            '/.secrets',
            ' . edgecase_ftw',
            '/file.tar.gz',
            '/path/to/file.txt',
            '/path/no_ext',
            '/stupid/path/with.dots/wazzup?',
            '/stupid/path/foo.with spaces',
            )
        for test in tests:
            result = Path(test).split_extension()
            expected = os.path.splitext(test)
            self.assertIsInstance(result[0], Path, test)
            self.assertIsInstance(result[1], six.string_types, test)
            self.assertSequenceEqual(expected, result, test)

    def test_strip_extension(self):
        tests = (
            ('', None, ''),
            ('/', None, '/'),
            ('file.txt/', None, 'file.txt/'),
            ('file.txt', None, 'file'),
            ('/file.txt', None, '/file'),
            ('/file.', None, '/file'),
            ('/file-1.0.3.txt', None, '/file-1.0.3'),
            ('/.secrets', None, '/.secrets'),
            (' . edgecase_ftw', None, ' '),
            ('/file.tar.gz', None, '/file.tar'),
            ('/file.tar.gz', ('.gz',), '/file.tar'),
            ('/file.tar.gz', ('.tar.gz',), '/file'),
            ('/file.tar.gz.haha', ('.tar.gz',), '/file.tar.gz.haha'),
            ('/file.tar.gz', (), '/file.tar.gz'),
            ('/file.tar.gz', ('tar',), '/file.tar.gz'),
            ('/file.tar.gz', ('gz',), '/file.tar.'),
            ('/file.tar.gz', ('ar.gz',), '/file.t'),
            )
        for test, match, expected in tests:
            result = Path(test).strip_extension(match)
            self.assertIsInstance(result, Path, (test, match))
            self.assertSequenceEqual(expected, result, (test, match))

    def test_join(self):
        tests = (
            (('', ''), ''),
            (('/', ''), '/'),
            (('path', '/'), 'path/'),
            (('path', '..'), ''),
            (('path', '../'), ''),
            (('path', '/..'), ''),
            (('path', '/../..'), '..'),
            (('path', '..', 'booyah'), 'booyah'),
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
            self.assertEqual(expected, t, bits)
        # test div operator which calls self.join
        t = Path('/foo/bar')
        self.assertEqual('/foo/car', t / '../car')

    def test_abspath(self):
        t = Path('/foo/bar')
        self.assertIsInstance(t.abspath(), Path)

    def test_normcase(self):
        t = Path('/foo/bar')
        self.assertIsInstance(t.normcase(), Path)

    def test_normpath(self):
        t = Path('/foo/bar')
        self.assertIsInstance(t.normpath(), Path)

    def test_realpath(self):
        t = Path('/foo/bar')
        self.assertIsInstance(t.realpath(), Path)

    def test_expand(self):
        t = Path('/foo/bar')
        self.assertIsInstance(t.expand(), Path)

    def test_glob(self):
        t = Path('/foo/bar')
        self.assertEqual([], list(t.glob('*')))

    def test_walk_iter(self):
        t = Path('/etc/passwd')
        for f in t.walk_iter():
            pass
        t = Path('/doesnot_exist')

    @unittest.skipIf(int(sys.version[0]) >= 3, 'walk_path deprecated in Python >= 3.x')
    def test_walk_path(self):
        Path('/etc/passwd').walk_path(lambda *s: s)
        Path('/doesnot_exist').walk_path(lambda *s: s)

    def test_list(self):
        Path('/tmp').list()
        self.assertRaises(OSError, Path('/doesnot_exist').list)

    @unittest.skipIf(sys.version.startswith('2.5'), 'Unsupported for Python 2.5 (see tmpfile)')
    def test_links(self):
        for method in ('link', 'hardlink', 'symlink'):
            fh = tmpfile()
            linkname = '/tmp/cuprum_test_links'
            try:
                t = Path(fh.name)
                f = getattr(t, method)(linkname)
                self.assertIsInstance(f, Path)
                self.assertEqual(linkname, f)
                f = getattr(t, method)(linkname, force=True)
                self.assertIsInstance(f, Path)
                self.assertEqual(linkname, f)
            finally:
                os.remove(fh.name)
                os.remove(linkname)

    def test_readlink(self):
        self.assertRaises(OSError, Path('/tmp').readlink)

    def test_chdir(self):
        self.assertTrue('/tmp' != os.getcwd())
        old_cwd = os.getcwd()
        try:
            Path('/tmp').chdir()
            self.assertEqual('/tmp', os.getcwd())
            self.assertRaises(OSError, Path('/doesnot_exist').chdir)
        finally:
            os.chdir(old_cwd)

    def test_fifo(self):
        name = '/tmp/cuprum_test_fifo'
        try:
            Path(name).fifo()
        finally:
            os.remove(name)

    def test_mknode(self):
        name = '/tmp/cuprum_test_mknode'
        try:
            Path(name).mknode()
        finally:
            os.remove(name)

    @unittest.skipIf(sys.version.startswith('2.5'), 'Unsupported for Python 2.5 (see tmpfile)')
    def test_touch(self):
        fh = tmpfile()
        try:
            t = Path(fh.name)
            t.touch(1970)
            foo = os.stat(fh.name)
            self.assertEqual(1970, foo.st_atime)
            self.assertEqual(1970, foo.st_mtime)
            t.touch(12, mtime=False)
            foo = os.stat(fh.name)
            self.assertEqual(12, foo.st_atime)
            self.assertEqual(1970, foo.st_mtime)
            t.touch(28, atime=False)
            foo = os.stat(fh.name)
            self.assertEqual(12, foo.st_atime)
            self.assertEqual(28, foo.st_mtime)
            t.touch()
            foo = os.stat(fh.name)
            self.assertNotEqual(12, foo.st_atime)
            self.assertNotEqual(28, foo.st_mtime)
        finally:
            os.remove(fh.name)

    def test_mkdir(self):
        t = Path('/tmp/cuprum_test_mkdir')
        if os.path.exists(str(t)):
            os.rmdir(str(t))
        t.mkdir()
        t.mkdir()  # silently ignores existing
