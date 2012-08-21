from __future__ import with_statement
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from cu import local, FG, BG, ERROUT
from cu import CommandNotFound, ProcessExecutionError, ProcessTimedOut

local.cwd.chdir('tests')


class LocalMachineTest(unittest.TestCase):
    def test_imports(self):
        from cu.syspath import ls
        self.assertTrue('test_local.py' in local['ls']().splitlines())
        self.assertTrue('test_local.py' in ls().splitlines())
        self.assertRaises(CommandNotFound, lambda: local['non_exist1N9'])
        try:
            from cu.syspath import non_exist1N9
        except CommandNotFound:
            pass
        else:
            self.fail('from cu.syspath import non_exist1N9')

    def test_cwd(self):
        from cu.syspath import ls
        self.assertEqual(local.cwd, os.getcwd())
        self.assertTrue('__init__.py' not in ls().splitlines())
        with local.cwd('../cu'):
            self.assertTrue('__init__.py' in ls().splitlines())
        self.assertTrue('__init__.py' not in ls().splitlines())
        self.assertRaises(OSError, local.cwd.chdir, '../non_exist1N9')

    def test_path(self):
        self.assertFalse((local.cwd / '../non_exist1N9').exists)
        self.assertTrue((local.cwd / '..' / 'cu').isdir)
        # traversal
        found = False
        for fn in local.cwd / '..' / 'cu':
            if fn.basename == '__init__.py':
                self.assertTrue(fn.isfile)
                found = True
        self.assertTrue(found)
        # glob'ing
        found = False
        for fn in local.cwd / '..' // '*/*.py':
            if fn.basename == 'local.py':
                found = True
        self.assertTrue(found)

    def test_env(self):
        self.assertTrue('PATH' in local.env)
        self.assertFalse('FOOBAR72' in local.env)
        self.assertRaises(ProcessExecutionError, local.python, '-c', 'import os;os.environ["FOOBAR72"]')
        local.env['FOOBAR72'] = 'spAm'
        self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR72"])').splitlines(), ['spAm'])
        with local.env(FOOBAR73=1889):
            self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1889'])
            with local.env(FOOBAR73=1778):
                self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1778'])
            self.assertEqual(local.python('-c', 'import os;print (os.environ["FOOBAR73"])').splitlines(), ['1889'])
        self.assertRaises(ProcessExecutionError, local.python, '-c', 'import os;os.environ["FOOBAR73"]')
        # path manipulation
        self.assertRaises(CommandNotFound, local.which, 'dummy-executable')
        with local.env():
            path = local.cwd / 'not-in-path'
            local.env.path.insert(0, path)
            self.assertEqual(path / 'dummy-executable', local.which('dummy-executable'))

    def test_local(self):
        self.assertTrue('cuprum' in str(local.cwd))
        self.assertTrue('PATH' in local.env.as_dict())
        local.which('ls')
        local['ls']
        self.assertEqual(local.python('-c', 'print ("hi there")').splitlines(), ['hi there'])

    def test_piping(self):
        from cu.syspath import ls, grep
        chain = ls | grep['\\.py']
        self.assertTrue('test_local.py' in chain().splitlines())
        chain = (ls['-a'] | grep['test'] | grep['local'])
        self.assertTrue('test_local.py' in chain().splitlines())

    def test_redirection(self):
        from cu.syspath import cat, ls, grep, rm
        chain = (ls | grep['\\.py']) > 'tmp.txt'
        chain()
        chain2 = (cat < 'tmp.txt') | grep['local']
        self.assertTrue('test_local.py' in chain2().splitlines())
        rm('tmp.txt')
        chain3 = (cat << 'this is the\nworld of helloness and\nspam bar and eggs') | grep['hello']
        self.assertTrue('world of helloness and' in chain3().splitlines())
        rc, _, err = (grep['-Zq5'] >= 'tmp2.txt').run(['-Zq5'], retcode=None)
        self.assertEqual(rc, 2)
        self.assertFalse(err)
        self.assertTrue('Usage' in (cat < 'tmp2.txt')())
        rm('tmp2.txt')
        rc, out, _ = (grep['-Zq5'] >= ERROUT).run(['-Zq5'], retcode=None)
        self.assertEqual(rc, 2)
        self.assertTrue('Usage' in out)

    def test_popen(self):
        from cu.syspath import ls
        p = ls.popen(['-a'])
        out, _ = p.communicate()
        self.assertEqual(p.returncode, 0)
        self.assertTrue('test_local.py' in out.decode(local.encoding).splitlines())

    def test_run(self):
        from cu.syspath import ls, grep
        rc, out, err = (ls | grep['non_exist1N9']).run(retcode=1)
        self.assertEqual(rc, 1)

    def test_timeout(self):
        from cu.syspath import sleep
        self.assertRaises(ProcessTimedOut, sleep, 10, timeout=0.1)

    def test_modifiers(self):
        from cu.syspath import ls, grep
        f = (ls['-a'] | grep['\\.py']) & BG
        f.wait()
        self.assertTrue('test_local.py' in f.stdout.splitlines())
        (ls['-a'] | grep['local'] > '/dev/null') & FG

    def test_session(self):
        sh = local.session()
        for _ in range(4):
            _, out, _ = sh.run('ls -a')
            self.assertTrue('test_local.py' in out.splitlines())
        sh.run('cd ..')
        sh.run('export FOO=17')
        out = sh.run('echo $FOO')[1]
        self.assertEqual(out.splitlines(), ['17'])

    def test_quoting(self):
        ssh = local['ssh']
        pwd = local['pwd']
        cmd = ssh['localhost', 'cd', '/usr', '&&',
                ssh['localhost', 'cd', '/', '&&',
                  ssh['localhost', 'cd', '/bin', '&&', pwd]]]
        expected = '''/usr/bin/ssh localhost cd /usr && /usr/bin/ssh localhost cd / '&&' /usr/bin/ssh localhost cd /bin "\'&&\'" /bin/pwd'''
        self.assertTrue("\"'&&'\"" in " ".join(cmd.formulate(0)))
        self.assertEqual(expected, ' '.join(cmd.formulate(0)))

    def test_tempdir(self):
        with local.tempdir() as dir:
            self.assertTrue(dir.isdir)
            with open(str(dir / 'test.txt'), 'w') as f:
                f.write('hello world')
            with open(str(dir / 'test.txt'), 'r') as f:
                self.assertEqual(f.read(), 'hello world')
        self.assertFalse(dir.exists)

    def test_tempfile(self):
        # text mode otherwise Py3 bitches about string not being bytes
        with local.tempfile('w+t') as fh:
            self.assertTrue(fh.name.isfile)
            fh.write('hello world')
            fh.seek(0)
            self.assertEqual(fh.read(), 'hello world')
        self.assertFalse(fh.name.exists)
