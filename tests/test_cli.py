import sys
import os.path
import textwrap
import time

import pexpect


PRODJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')


def test_cli(tmpdir, monkeypatch):
    monkeypatch.chdir(PRODJECT_ROOT)
    notebook_path = tmpdir.join('notebook.py')

    notebook_path.write(textwrap.dedent("""\
            #: one
            x = 1
            #: two
            print(x)
        """))

    p = pexpect.spawn(
        sys.executable, ['-m', 'intercessor', str(notebook_path)],
        encoding='utf-8', timeout=1)

    p.expect('>>> at .+')
    p.sendline('one')
    p.expect('>>> running .+>>> at .+$')
    p.sendline('two')
    p.expect('>>> running .+>>> at .+$')
    assert p.after.splitlines()[-2] == '1'

    notebook_path.write(textwrap.dedent("""\
        #: one
        x = 2
        #: two
        print(x)
    """))

    p.sendline('one')
    p.expect('>>> running .+>>> at .+$')
    p.sendline('two')
    p.expect('>>> running .+>>> at .+$')
    assert p.after.splitlines()[-2] == '2'

    notebook_path.write(textwrap.dedent("""\
        #: one
        x = 1
        #: two
        print(x)
    """))

    p.sendline()
    p.expect('>>> running .+>>> at .+$')
    assert p.after.splitlines()[-2] == '2'

    p.sendintr()
    time.sleep(.1)
    assert p.isalive()

    p.sendintr()
    time.sleep(.1)
    assert not p.isalive()

