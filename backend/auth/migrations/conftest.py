# conftest.py — local pytest configuration for the migrations smoke-test directory.
#
# This file intentionally left minimal. The pytest.ini in this same directory
# sets rootdir and testpaths so pytest does not traverse parent packages
# (which would trigger the heavy ML backend imports).

