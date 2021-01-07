#!/usr/bin/env python3

"""tests for corems_run.py"""

import hashlib
import os
import random
import re
import string
import glob
from subprocess import getstatusoutput

prg = '../corems_run.py'
directory = 'test_dir'
calib_file = 'test_calib.txt'
output_dirname = "core_ms"


# --------------------------------------------------
def test_exists():
    """Exists"""

    assert os.path.isfile(prg)


# --------------------------------------------------
def test_usage():
    """Usage"""

    for flag in ['-h', '--help']:
        rv, out = getstatusoutput(f'{prg} {flag}')
        assert rv == 0
        assert re.match("usage", out, re.IGNORECASE)


# --------------------------------------------------
def test_print_version():
    """CoreMS version"""

    rv, out = getstatusoutput(f'{prg} {directory}')
    assert rv == 0
    assert re.findall("CoreMS version", out)


# --------------------------------------------------
def test_no_calib_default():
    """Without calibration with default"""

    rv, out = getstatusoutput(f'{prg} {directory}')
    assert rv == 0
    assert re.findall("Without calibration", out)


# --------------------------------------------------
def test_no_calib_with_argument():
    """Without calibration with argument"""

    arg = False

    rv, out = getstatusoutput(f'{prg} {directory} -c {arg}')
    assert rv == 0
    assert re.findall("Without calibration", out)


# --------------------------------------------------
def test_calib_without_ref():
    """Missing calibration file"""

    arg = True

    rv, out = getstatusoutput(f'{prg} {directory} -c {arg}')
    assert rv != 0  # == 1
    assert re.findall("__main__.NeedCalibrationFile", out)


# --------------------------------------------------
def test_calib_default():
    """With calibration with default ppm"""

    arg = True

    rv, out = getstatusoutput(f'{prg} {directory} -ref {calib_file} -c {arg}')
    assert rv == 0
    assert re.findall("With calibration", out)


# --------------------------------------------------
def test_calib_ppm():
    """With calibration with custom ppm"""

    arg = True
    n = 2

    rv, out = getstatusoutput(f'{prg} {directory} -ref {calib_file} -c {arg} -ppm {n}')
    assert rv == 0
    assert re.findall(f"With calibration at {n} ppm", out)


# --------------------------------------------------
def test_run_concluded():
    """CoreMS Concluded!"""

    rv, out = getstatusoutput(f'{prg} {directory}')
    assert rv == 0
    assert re.findall(f"CoreMS Concluded!", out)


# --------------------------------------------------
def test_default_output_dir_exists():
    """Test if output dir exists"""

    assert os.path.exists("corems_output")


# --------------------------------------------------
def test_output_files_not_empty():
    """Gotta have something in them"""

    output_files = glob.glob("corems_output/*.csv")

    for file in output_files:
        file_size = os.stat(file).st_size
        assert file_size != 0


# --------------------------------------------------
