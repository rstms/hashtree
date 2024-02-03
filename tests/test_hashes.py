# test all hash types

from tempfile import NamedTemporaryFile

from hashtree import hashtree




def test_hashes_list():
    hashes = ["md5", "sha1"]
    for hash in hashes:
        ret = hashtree(hash=hash)
        assert ret
