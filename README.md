hashtree
========

Generate BSD-style hash digest checksums for a list of files


![Image](https://img.shields.io/github/license/rstms/hashtree)

![Image](https://img.shields.io/pypi/v/hashtree.svg)



![Image](https://readthedocs.org/projects/hashtree/badge/?version=latest)

![Image](https://pyup.io/repos/github/rstms/hashtree/shield.svg)


* Free software: MIT license
* Documentation: https://hashtree.readthedocs.io.
```
Usage: hashtree [OPTIONS] [INFILE] [OUTFILE]

  generate hash digest for list of files

Options:
  --version                       Show the version and exit.
  -d, --debug                     debug mode
  --shell-completion TEXT         configure shell completion
  -h, --hash [sha512|md5|sha256|blake2b|sha3_256|sha224|blake2s|sha1|sha384|sha3_224|sha3_512|sha3_384]
                                  select checksum hash
  -p, --progress / -P, --no-progress
                                  show/hide progress bar
  -a, --ascii                     ASCII progress bar
  -f, --find / -F, --no-find      generate file list with 'find'
  -s, --sort-files / -S, --no-sort-files
                                  sort input/generated file list
  -o, --sort-output / -O, --no-sort-output
                                  sort output with 'sort'
  -b, --base-dir DIRECTORY        base directory for file list
  --help                          Show this message and exit.
```
