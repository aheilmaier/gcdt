# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import subprocess
import random
import shutil
import string
from tempfile import NamedTemporaryFile, mkdtemp

import pytest


# http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991
class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def create_tempfile(contents):
    """Helper to create a named temporary file with contents.
    Note: caller has responsibility to clean up the temp file!

    :param contents: define the contents of the temporary file
    :return: filename of the temporary file
    """

    # helper to create a named temp file
    tf = NamedTemporaryFile(delete=False)
    with open(tf.name, 'w') as tfile:
        tfile.write(contents)

    return tf.name


def get_size(start_path='.'):
    """Accumulate the size of the files in the folder.

    :param start_path:
    :return: size
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def random_string():
    """Create a random 6 character string.

    note: in case you use this function in a test during test together with
    an awsclient then this function is altered so you get reproducible results
    that will work with your recorded placebo json files (see helpers_aws.py).
    """
    return ''.join([random.choice(string.ascii_lowercase) for i in xrange(6)])


@pytest.fixture(scope='module')  # 'function' or 'module'
def cleanup_tempfiles():
    items = []
    yield items
    # cleanup
    for i in items:
        os.unlink(i)


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_folder():
    # provide a temp folder and cleanup after test
    # this also changes into the folder and back to cwd during cleanup
    cwd = (os.getcwd())
    folder = mkdtemp()
    os.chdir(folder)
    yield folder, cwd
    # cleanup
    os.chdir(cwd)  # cd to original folder
    shutil.rmtree(folder)


@pytest.fixture(scope='function')  # 'function' or 'module'
def random_file():
    # provide a named file with some random content
    # we use random_string so it is reproducible
    filename = create_tempfile(random_string())
    yield filename
    # cleanup
    os.unlink(filename)


def _npm_check():
    # Make sure the npm tool is installed.
    # returns false if missing
    try:
        subprocess.call(["npm", "--version"])
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return True
        else:
            # Something else went wrong while trying to run `npm`
            raise
    return False


# skipif helper check_npm
check_npm = pytest.mark.skipif(
    _npm_check(),
    reason="You need to install npm (see gcdt docs)."
)
