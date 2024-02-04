# cli tests

import os
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from click.testing import CliRunner

import hashtree
from hashtree import __version__, cli
from hashtree.cli import DEFAULT_SORT_ARGS
from hashtree.hash import DEFAULT_HASH


def sstrs(data):
    return data.strip().split("\n")


def fstrs(filename):
    return sstrs(Path(filename).read_text())


def sumfiles(sums):
    if isinstance(sums, str) and Path(sums).is_file():
        sums = fstrs(sums)
    assert isinstance(sums, list)
    ret = []
    for sum in sums:
        assert isinstance(sum, str)
        _, _, tail = sum.partition("(")
        file, _, _ = tail.partition(")")
        ret.append(file)
    return ret


def shellsorted(lines):
    if isinstance(lines, str) and Path(lines).is_file():
        lines = fstrs(lines)
    assert isinstance(lines, list)
    for line in lines:
        assert isinstance(line, str)
        assert len(line) > 1
    with NamedTemporaryFile("w+") as ifp, NamedTemporaryFile("w+", delete_on_close=False) as ofp:
        ifp.write("\n".join(lines) + "\n")
        ifp.flush()
        ifp.seek(0)
        cmd = shlex.split(DEFAULT_SORT_ARGS)
        cmd.insert(0, "sort")
        subprocess.run(cmd, stdin=ifp, stdout=ofp, text=True, check=True)
        ofp.close()
        output = fstrs(ofp.name)
    return output


def pysorted(lines):
    if isinstance(lines, str) and Path(lines).is_file():
        lines = fstrs(lines)
    assert isinstance(lines, list)
    for line in lines:
        assert isinstance(line, str)
        assert len(line) > 1
    return sorted(lines)


def test_shellsorted():
    list = ["aaa", "zzz", "iii"]
    sorted = shellsorted(list)
    assert list != sorted
    sorted2 = shellsorted(sorted)
    assert sorted2 == sorted
    assert set(list) == set(sorted)
    assert set(list) == set(sorted2)


def test_version():
    """Test reading version and module name"""
    assert hashtree.__name__ == "hashtree"
    assert __version__
    assert isinstance(__version__, str)


@pytest.fixture
def run():
    runner = CliRunner()

    env = os.environ.copy()
    env["TESTING"] = "1"

    def _run(cmd, **kwargs):
        assert_exit = kwargs.pop("assert_exit", 0)
        assert_exception = kwargs.pop("assert_exception", None)
        env.update(kwargs.pop("env", {}))
        kwargs["env"] = env
        result = runner.invoke(cli, cmd, **kwargs)
        if assert_exception is not None:
            assert isinstance(result.exception, assert_exception)
        elif result.exception is not None:
            raise result.exception from result.exception
        elif assert_exit is not None:
            assert result.exit_code == assert_exit, (
                f"Unexpected {result.exit_code=} (expected {assert_exit})\n"
                f"cmd: '{shlex.join(cmd)}'\n"
                f"output: {str(result.output)}"
            )
        return result

    return _run


@pytest.fixture
def is_sorted():
    def _is_sorted(filename):
        if isinstance(filename, list):
            lines = filename
        elif Path(filename).is_file():
            lines = fstrs(filename)
        else:
            lines = sstrs(filename)
        assert len(lines)
        return lines == shellsorted(lines)

    return _is_sorted


@pytest.fixture
def base():
    return "/tmp/test/src"


@pytest.fixture
def files(shared_datadir):
    return str(shared_datadir / "files")


@pytest.fixture
def sums(shared_datadir):
    return str(shared_datadir / "sums")


@pytest.fixture
def find_list(base):
    output = subprocess.check_output(["find", ".", "-type", "f"], cwd=base, text=True)
    flist = sstrs(output)
    assert flist != shellsorted(flist)
    assert flist != pysorted(flist)
    return flist


def test_cli_no_args(run):
    result = run([])
    # SHA256 (VERSION) = 4cac276b6ec5d4c71cd96ca2e7b762eb125439adbc8721de5613106d1345fe2d
    for line in sstrs(result.output):
        assert re.match(r"^SHA256 \([^)]+\) = [0-9a-f]+$", line)


def test_cli_help(run):
    result = run(["--help"])
    assert "Show this message and exit." in result.output


def test_cli_exception(run):

    cmd = ["--shell-completion", "and_now_for_something_completely_different"]

    with pytest.raises(RuntimeError) as exc:
        result = run(cmd)
    assert isinstance(exc.value, RuntimeError)

    # example of testing for expected exception
    result = run(cmd, assert_exception=RuntimeError)
    assert result.exception
    assert result.exc_info[0] == RuntimeError
    assert result.exception.args[0] == "cannot determine shell"

    with pytest.raises(AssertionError) as exc:
        result = run(cmd, assert_exception=ValueError)
    assert exc


def test_cli_exit(run):
    result = run(["--help"], assert_exit=None)
    assert result
    result = run(["--help"], assert_exit=0)
    assert result
    with pytest.raises(AssertionError):
        run(["--help"], assert_exit=-1)


def test_cli_sort_shellsorted(shared_datadir, is_sorted):
    file = shared_datadir / "order"
    file.write_text("aaa\nzzz\n")
    assert is_sorted(file) is True
    file.write_text("zzz\naaa\n")
    assert is_sorted(file) is False


def test_cli_sort_files_find(run, base, files, sums, is_sorted, validate_hash_file):
    run(["-b", base, files, sums])
    validate_hash_file(DEFAULT_HASH, sums)
    assert is_sorted(files)
    assert is_sorted(sums)


def test_sort_files_stdin(run, base, files, sums, is_sorted, find_list, validate_hash_file):
    assert find_list != shellsorted(find_list)
    input_data = "\n".join(find_list) + "\n"
    # files from stdin, default sort_files
    run(["--no-find", "-b", base, "-", sums], input=input_data)
    validate_hash_file(DEFAULT_HASH, sums)
    assert not is_sorted(sstrs(input_data))
    assert is_sorted(sums)
    sum_files = sumfiles(sums)
    assert find_list != sum_files
    assert sorted(find_list) == sorted(sum_files)

    # files from stdin, no-sort-files
    run(["--no-find", "--no-sort-files", "-b", base, "-", sums], input=input_data)
    validate_hash_file(DEFAULT_HASH, sums)

    assert not is_sorted(sstrs(input_data))
    assert not is_sorted(sums)
    sum_files = sumfiles(sums)
    assert find_list == sum_files


def test_sort_files_file(run, base, files, sums, find_list, is_sorted, validate_hash_file):
    Path(files).write_text("\n".join(find_list) + "\n")
    assert not is_sorted(files)
    run(["--no-find", "-b", base, files, sums])
    assert is_sorted(files)
    assert is_sorted(sums)

    Path(files).write_text("\n".join(find_list) + "\n")
    assert not is_sorted(files)
    run(["--no-find", "--no-sort-files", "-b", base, files, sums])
    assert not is_sorted(files)
    assert not is_sorted(sums)


def test_sort_output_findsort(run, base, files, sums, is_sorted, validate_hash_file):
    run(["-b", base, files, sums])
    assert is_sorted(files)
    assert is_sorted(sums)
    run(["--sort-output", "-b", base, files, sums])
    assert is_sorted(files)
    assert is_sorted(sums)


def test_sort_output_findnosort(run, base, files, sums, is_sorted, validate_hash_file):
    run(["--no-sort-files", "-b", base, files, sums])
    assert not is_sorted(files)
    assert not is_sorted(sums)
    run(["--no-sort-files", "--sort-output", "-b", base, files, sums])
    assert not is_sorted(files)
    assert is_sorted(sums)


def test_sort_output_stdout(run, base, find_list, is_sorted):
    assert not is_sorted(find_list)
    result = run(["--no-sort-files", "-b", base])
    sums = sstrs(result.stdout)
    assert sums != shellsorted(sums)
    assert sumfiles(sums) == find_list

    result = run(["--no-sort-files", "--sort-output", "-b", base])
    sums = sstrs(result.stdout)
    assert is_sorted(sums)
    assert sumfiles(sums) != find_list
    assert shellsorted(sumfiles(sums)) == shellsorted(find_list)
