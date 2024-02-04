"""hashtree command"""

import atexit
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import click
import click.core

from .clio import CLIO
from .exception_handler import ExceptionHandler
from .hash import DEFAULT_HASH, HASHES, HashDigest
from .progress import ProgressReader
from .shell import _shell_completion
from .version import __timestamp__, __version__

header = f"{__name__.split('.')[0]} v{__version__} {__timestamp__}"


def _ehandler(ctx, option, debug):
    ctx.obj = dict(ehandler=ExceptionHandler(debug))
    ctx.obj["debug"] = debug


HASH_CHOICES = list(HASHES)

DEFAULT_SORT_ARGS = "-ifdk1.1"


@click.command("hashtree", context_settings={"auto_envvar_prefix": "HASHTREE", "show_default": True})
@click.version_option(message=header)
@click.option(
    "-d",
    "--debug",
    is_eager=True,
    is_flag=True,
    callback=_ehandler,
    help="debug mode",
)
@click.option(
    "--shell-completion",
    is_flag=False,
    flag_value="[auto]",
    callback=_shell_completion,
    help="configure shell completion",
)
@click.option(
    "-h",
    "--hash",
    type=click.Choice(HASH_CHOICES),
    default=DEFAULT_HASH,
    help="select checksum hash",
)
@click.option("-p/-P", "--progress/--no-progress", is_flag=True, help="show/hide progress bar")
@click.option("-a", "--ascii", is_flag=True, help="ASCII progress bar")
@click.option("-w", "--width", type=int, help="progress bar width")
@click.option("-f/-F", "--find/--no-find", is_flag=True, default=True, help="generate file list with 'find'")
@click.option(
    "-s/-S", "--sort-files/--no-sort-files", is_flag=True, default=True, help="sort input/generated file list"
)
@click.option("-o/-O", "--sort-output/--no-sort-output", is_flag=True, default=False, help="sort output with 'sort'")
@click.option("-k", "--sort-args", default=DEFAULT_SORT_ARGS, help="args passed to sort")
@click.option(
    "-b",
    "--base-dir",
    type=click.Path(file_okay=False, readable=True),
    default=".",
    help="base directory for file list",
)
@click.argument("INFILE", type=click.Path(dir_okay=False), default="-")
@click.argument("OUTFILE", type=click.Path(dir_okay=False, writable=True), default="-")
@click.pass_context
def cli(
    ctx,
    debug,
    shell_completion,
    base_dir,
    ascii,
    find,
    hash,
    sort_files,
    sort_output,
    sort_args,
    progress,
    width,
    infile,
    outfile,
):
    """generate hash digest for list of files"""

    return hashtree(
        base_dir,
        infile,
        outfile,
        ascii=ascii,
        find=find,
        hash=hash,
        sort_files=sort_files,
        sort_output=sort_output,
        sort_args=sort_args,
        progress=progress,
        width=width
    )


def hashtree(
    base_dir,
    infile,
    outfile,
    *,
    ascii=False,
    find=True,
    hash=None,
    sort_files=True,
    sort_output=False,
    sort_args=None,
    progress=False,
    width=None,
):
    base = Path(base_dir)
    if sort_args is None:
        sort_args = DEFAULT_SORT_ARGS

    if progress is None and is_stdio(outfile):
        progress = False

    if find:
        infile = find_files(base, infile)
    elif is_stdio(infile):
        infile = spool_stdin()

    if sort_files:
        sort_file(infile, sort_args)

    # if sorting output, redirect to tempfile
    if sort_output:
        sorted_outfile = outfile
        outfile = create_tempfile()
    else:
        sorted_outfile = None

    progress_kwargs = {}

    if ascii:
        progress_kwargs["ascii"] = True
    if progress is not None:
        progress_kwargs["disable"] = not progress
    if width is not None:
        progress_kwargs["ncols"] = width

    generate_hash_digests(base, infile, outfile, hash, progress_kwargs)

    if sorted_outfile:
        write_sorted_output(outfile, sorted_outfile, sort_args)


def generate_hash_digests(base, infile, outfile, hash, progress_kwargs):
    hasher = HashDigest(base, hash)
    with CLIO(infile, outfile) as clio:
        with ProgressReader(clio.ifp, **progress_kwargs) as reader:
            for filename in reader.readlines():
                if filename.startswith(str(base)):
                    filename = Path(filename).relative_to(base)
                digest = hasher.file_digest(filename)
                clio.ofp.write(digest + "\n")


def write_sorted_output(spool, outfile, sort_args):
    sort_file(spool, sort_args)
    with Path(spool).open("r") as ifp:
        if is_stdio(outfile):
            copy_stream(ifp, sys.stdout)
        else:
            with Path(outfile).open("w") as ofp:
                copy_stream(ifp, ofp)


def copy_stream(in_stream, out_stream):
    while True:
        buf = in_stream.read()
        if buf:
            out_stream.write(buf)
        else:
            return


def spool_stdin():
    tempfile = create_tempfile()
    with Path(tempfile).open("w") as ofp:
        copy_stream(sys.stdin, ofp)
    return tempfile


def is_stdio(filename):
    return filename in ("-", None)


def sort_file(filename, sort_args):

    if is_stdio(filename):
        raise RuntimeError("cannot sort stdio")

    cmd = shlex.split(sort_args)
    cmd.insert(0, "sort")

    # use system sort to handle huge streams
    with NamedTemporaryFile(delete=False, dir=".") as ofp:
        with Path(filename).open("r") as ifp:
            subprocess.run(cmd, stdin=ifp, stdout=ofp, check=True, text=True)
        ofp.close()
        tempfile = Path(ofp.name)
        try:
            tempfile.rename(filename)
        except OSError as exc:
            if exc.errno == 18:  # Invalid cross-device link
                shutil.copyfile(tempfile, filename)
                tempfile.unlink()
            else:
                raise


def create_tempfile():
    filename = NamedTemporaryFile(delete=False, dir=".", prefix="hashtree_file_list").name
    atexit.register(reaper, filename)
    return filename


def find_files(base, filename):

    if filename in [".", "-", None]:
        filename = create_tempfile()

    with Path(filename).open("w") as ofp:
        subprocess.run(["find", ".", "-type", "f"], cwd=str(base), stdout=ofp, check=True, text=True)

    return filename


def reaper(filename):
    """delete a file"""
    Path(filename).unlink()


if __name__ == "__main__":
    sys.exit(cli())  # pragma: no cover
