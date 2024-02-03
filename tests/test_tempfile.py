# temp file tests

from hashtree import hashtree
from hashtree.hash import DEFAULT_HASH


def test_temp_rename(shared_datadir, validate_hash_file):

    base = "/tmp/test/src"
    files = shared_datadir / "files"
    sums = shared_datadir / "sums"
    hashtree(base, files, sums, find=True, sort=True)
    validate_hash_file(DEFAULT_HASH, sums)
