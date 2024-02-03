# pytest config

import re
from pathlib import Path

import pytest


@pytest.fixture
def validate_hash_line():
    def _validate_hash_line(hash, line):
        assert re.match("^" + hash.upper() + r"\s\([^)]+\) = [0-9a-f]+$", line)
        return True

    return _validate_hash_line


@pytest.fixture
def validate_hash_file(validate_hash_line):
    def _validate_hash_file(hash, filename):
        with Path(filename).open("r") as ifp:
            for line in ifp:
                assert validate_hash_line(hash, line)

    return _validate_hash_file
