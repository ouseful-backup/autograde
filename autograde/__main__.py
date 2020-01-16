#!/usr/bin/env python3
# Standard library modules.
import os
import sys
import argparse
import subprocess
from pathlib import Path
from functools import reduce

# Third party modules.

# Local modules
from autograde.util import logger, loglevel, project_root, cd

# Globals and constants variables.
CONTAINER_TAG = 'autograde'


def build(args):
    cmd = [args.backend, 'build', '-t', CONTAINER_TAG, '.']

    with cd(project_root()):
        return subprocess.run(cmd, capture_output=args.quiet).returncode


def test(args):
    path_tst = Path(args.test).expanduser().absolute()
    path_nbk = Path(args.notebook).expanduser().absolute()
    path_tgt = Path(args.target or Path.cwd()).expanduser().absolute()
    path_cxt = Path(args.context).expanduser().absolute() if args.context else None

    assert path_tst.is_file(), f'{path_tst} is no regular file'
    assert path_nbk.is_file() or path_nbk.is_dir(), f'{path_nbk} is no regular file or directory'
    assert path_tgt.is_dir(), f'{path_tgt} is no regular directory'
    assert path_cxt is None or path_cxt.is_dir(), f'{path_cxt} is no regular directory'

    if path_nbk.is_file():
        notebooks = [path_nbk]

    else:
        notebooks = list(filter(
            lambda p: '.ipynb_checkpoints' not in p.parts,
            path_nbk.rglob('*.ipynb')
        ))

    def run(path_nb_):
        cmd = [
            args.backend, 'run',
            '-v', f'{path_tst}:/autograde/test.py',
            '-v', f'{path_nb_}:/autograde/notebook.ipynb',
            '-v', f'{path_tgt}:/autograde/target',
            *(('-v', f'{path_cxt}:/autograde/context:ro') if path_cxt else ()),
            '-u', str(os.geteuid()),
            CONTAINER_TAG
        ]

        logger.info(f'test: {path_nb_}')
        logger.debug(' '.join(cmd))

        return subprocess.run(cmd).returncode

    return reduce(max, map(run, notebooks))


def main():
    parser = argparse.ArgumentParser(description='run tests on jupyter notebook')

    parser.add_argument('-v', '--verbose', action='count', default=0, help='verbosity level')
    parser.add_argument('-e', '--backend', type=str, default='docker', choices=['docker', 'podman'],
                        metavar='', help='backend to use')

    subparsers = parser.add_subparsers(help='sub command help')

    bld_parser = subparsers.add_parser('build')
    bld_parser.add_argument('-q', '--quiet', action='store_true', help='mute output')
    bld_parser.set_defaults(func=build)

    exe_parser = subparsers.add_parser('test')
    exe_parser.add_argument('test', type=str, help='autograde test script')
    exe_parser.add_argument(
        'notebook', type=str,
        help='the jupyter notebook to be tested or a directory to be searched for notebooks'
    )
    exe_parser.add_argument('-t', '--target', type=str, metavar='', help='where to store results')
    exe_parser.add_argument('-c', '--context', type=str, metavar='', help='context directory')
    exe_parser.set_defaults(func=test)

    args = parser.parse_args()

    logger.setLevel(loglevel(args.verbose))
    logger.debug(f'args: {args}')

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
