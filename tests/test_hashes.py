# test all hash types

from pathlib import Path

from hashtree import hashtree
from hashtree.hash import HASHES


def test_hashes_list(shared_datadir, validate_hash_file):
    for hash in HASHES:
        output = (shared_datadir / "test").with_suffix("." + hash)
        hashtree(".", None, output, find=True, hash=hash)
        validate_hash_file(hash, output)
        sums = Path("./tests/data") / output.name
        sums.write_text(output.read_text())
