from __future__ import with_statement
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import pwd
import grp
import tempfile

from cu import Path


# NOTE: all tests assume *unix OS.


def tmpfile(delete=False):
    return tempfile.NamedTemporaryFile(delete=delete, prefix='cuprum_test_')


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
            ('/path/to/file.txt', 'file.txt'),
            ('path/', ''),  # different than unix basename
            ('/path/trailing', 'trailing'),
            ('/stupid/path/with.dots/wazzup?', 'wazzup?'),
            ('/stupid/path/with spaces', 'with spaces'),
            )
        for test, expected in tests:
            t = Path(test).basename
            self.assertIsInstance(t, basestring)
            self.assertEqual(expected, t, test)

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
            t = Path(test).dirname
            self.assertIsInstance(t, Path)
            self.assertEqual(expected, t)

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
            self.assertTrue(t.isabs)
            self.assertFalse(t.isrelative)
        for path in relative:
            t = Path(path)
            self.assertFalse(t.isabsolute)
            self.assertTrue(t.isrelative)

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
        expected = ['/', 'some', ' path', ' ', 'awesome.txt']
        self.assertSequenceEqual(expected, Path('/some/ path/ /awesome.txt').split())

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

    @unittest.skip('TODO:')
    def test_expand(self):
        pass

    def test_glob(self):
        t = Path('/foo/bar')
        self.assertEqual([], t.glob('*'))

    def test_up(self):
        self.assertEqual('/foo/', Path('/foo/bar').up())
        self.assertEqual('/', Path('/foo/bar').up(2))
        self.assertEqual('/', Path('/foo/bar').up(8))

    def test_walk_iter(self):
        t = Path('/etc/passwd')
        for f in t.walk_iter():
            pass
        t = Path('/doesnot_exist')

    def test_walk_path(self):
        Path('/etc/passwd').walk_path(lambda *s: s)
        Path('/doesnot_exist').walk_path(lambda *s: s)

    def test_list(self):
        Path('/tmp').list()
        self.assertRaises(OSError, Path('/doesnot_exist').list)

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
