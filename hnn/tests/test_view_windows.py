import os.path as op
import os
import sys
import shlex
from subprocess import Popen, PIPE

from mne.utils import _fetch_file


def fetch_file(fname):
    data_dir = ('https://raw.githubusercontent.com/jonescompneurolab/'
                'hnn/test_data/')

    data_url = op.join(data_dir, fname)
    if not op.exists(fname):
        _fetch_file(data_url, fname)


def view_window(code_fname, paramf, data_fname=None):
    """Test to check that viewer displays without error"""

    nrniv_str = 'nrniv -python -nobanner'
    cmd = nrniv_str + ' ' + sys.executable + ' ' + code_fname + ' ' + \
        paramf
    if data_fname is not None:
        cmd += ' ' + data_fname

    # Windows will fail to load the correct Qt plugin when launched with nrniv
    # This is a temporary fix until separate windows are no longer launched
    # as different processes
    basedir = os.path.expanduser('~')
    plugin_dir = op.join(basedir, 'Miniconda3', 'envs', 'hnn', 'Library',
                         'plugins', 'platforms')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_dir

    # Split the command into shell arguments for passing to Popen
    cmdargs = shlex.split(cmd, posix="win" not in sys.platform)

    # Start the simulation
    proc = Popen(cmdargs, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                 cwd=os.getcwd(), universal_newlines=True)
    out, err = proc.communicate()

    # print all messages (including error messages)
    print('STDOUT', out)
    print('STDERR', err)

    if proc.returncode != 0:
        raise RuntimeError("Running command %s failed" % cmd)


def test_view_rast():
    fname = 'spk.txt'
    fetch_file(fname)
    paramf = op.join('param', 'default.param')
    view_window('visrast.py', paramf, fname)


def test_view_dipole():
    fname = 'dpl.txt'
    fetch_file(fname)
    paramf = op.join('param', 'default.param')
    view_window('visdipole.py', paramf, fname)


def test_view_psd():
    paramf = op.join('param', 'default.param')
    view_window('vispsd.py', paramf)


def test_view_spec():
    paramf = op.join('param', 'default.param')
    view_window('visspec.py', paramf)
