"""hashtree command"""

import atexit
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


@click.command("hashtree", context_settings={"auto_envvar_prefix": "HASHTREE"})
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
@click.option("-p/-P", "--progress/--no-progress", is_flag=True, default=True, help="animated progress display")
@click.option("-a", "--ascii", is_flag=True, help="ASCII progress bar")
@click.option("-f", "--find", is_flag=True, help="use 'find BASE_DIR --type f' to generate file list")
@click.option("-s/-S", "--sort/--no-sort", is_flag=True, default=True, help="sort generated files")
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
    sort,
    progress,
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
        sort=sort,
        progress=progress,
    )


def hashtree(
    base_dir,
    infile,
    outfile,
    *,
    ascii=None,
    find=None,
    hash=None,
    sort=None,
    progress=None,
):
    base = Path(base_dir)

    if infile == "-" and outfile == "-":
        find = True

    if outfile == "-":
        progress = False

    if find:
        infile = find_files(base, infile)
        if sort:
            sort_file(infile)

    hasher = HashDigest(base, hash)

    kwargs = {}

    if ascii:
        kwargs["ascii"] = True
    if not progress:
        kwargs["disable"] = True

    with CLIO(infile, outfile) as clio:
        with ProgressReader(clio.ifp, **kwargs) as reader:
            for filename in reader.readlines():
                if filename.startswith(str(base)):
                    filename = Path(filename).relative_to(base)
                digest = hasher.file_digest(filename)
                clio.ofp.write(digest + "\n")

    if sort and outfile != "-":
        sort_file(outfile)


def sort_file(filename):

    if filename in ["-", None]:
        raise click.ClickException("cannot sort stdin/stdout")

    with NamedTemporaryFile(delete=False, dir=".") as ofp:
        with Path(filename).open("r") as ifp:
            subprocess.run(["sort"], stdin=ifp, stdout=ofp, check=True, text=True)
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


def find_files(base, filename):

    if filename in [".", "-", None]:
        filename = NamedTemporaryFile(delete=False, dir=".", prefix="hashtree_file_list").name
        atexit.register(reaper, filename)

    with Path(filename).open("w") as ofp:
        subprocess.run(["find", ".", "-type", "f"], cwd=str(base), stdout=ofp, check=True, text=True)

    return filename


def reaper(filename):
    """delete a file"""
    Path(filename).unlink()


if __name__ == "__main__":
    sys.exit(hashtree())  # pragma: no cover
