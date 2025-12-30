import argparse
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

import pysmt.environment
import pysmt.shortcuts as smt
from array import array
from pysdd.sdd import SddManager, Vtree, SddNode
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import nnf2bcs12
from src import utils
from src.decdnnf import decdnnf


@dataclass(frozen=True)
class ArgumentsWithSDD:
    mapping: dict[int, FNode]
    vtree: Path
    sdd: Path
    exists_x_vtree: Path
    exists_x_sdd: Path


@dataclass(frozen=True)
class ArgumentsWithD4:
    mapping: dict[int, FNode]
    nnf: Path
    exists_x_nnf: Path


def d4(args: ArgumentsWithD4):
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        exists_x_bc: Path = folder / 'exists_x.bc'

        with utils.log('nnf -> BC-S1.2'):
            nnf2bcs12.translate(
                nnf=args.nnf,
                project=[k for k, v in args.mapping.items() if v.is_symbol(smt.BOOL)],
                bcs12=exists_x_bc,
            )

        with utils.log('existentially quantifying out x'):
            process: CompletedProcess[str] = subprocess.run(
                [
                    'd4',
                    '--input', exists_x_bc,
                    '--input-type', 'circuit',
                    '--remove-gates', '1',
                    '--dump-file', args.exists_x_nnf,
                ],
                capture_output=True,
                text=True,
            )

        assert 0 == process.returncode, '\n'.join((process.stdout, process.stderr))


def sdd(args: ArgumentsWithSDD):
    with utils.log('load vtree'):
        vtree: Vtree = Vtree.from_file(args.vtree.as_posix())
        mgr: SddManager = SddManager.from_vtree(vtree)

    with utils.log('load sdd'):
        phi: SddNode = mgr.read_sdd_file(str.encode(args.sdd.as_posix()))

    with utils.log('existentially quantifying out x'):
        which: list[int] = [0] * (1 + len(args.mapping))
        for k, v in args.mapping.items():
            if not v.is_symbol(smt.BOOL):
                which[k] = 1

        exists_x_phi: SddNode = mgr.exists_multiple(array('i', which), phi)

    with utils.log('store'):
        vtree.save(str.encode(args.exists_x_vtree.as_posix()))
        exists_x_phi.save(str.encode(args.exists_x_sdd.as_posix()))


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--steps', type=Path, required=True)
        parser.add_argument('--mapping', type=utils.file, required=True)

        with utils.use(parser.add_subparsers(dest='compiler', required=True)) as sub:
            with utils.use(sub.add_parser('d4')) as subparser:
                subparser.add_argument('--nnf', type=utils.file, required=True)
                subparser.add_argument('--exists_x_nnf', type=Path, required=True)

            with utils.use(sub.add_parser('sdd')) as subparser:
                subparser.add_argument('--vtree', type=utils.file, required=True)
                subparser.add_argument('--sdd', type=utils.file, required=True)
                subparser.add_argument('--exists_x_vtree', type=Path, required=True)
                subparser.add_argument('--exists_x_sdd', type=Path, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    with utils.log('total'):

        env: Environment = pysmt.environment.get_env()
        mapping: dict[int, FNode] = decdnnf.mapping(env=env, mapping=args.mapping)

        match args.compiler:
            case 'd4':
                d4(
                    ArgumentsWithD4(
                        mapping=mapping,
                        nnf=args.nnf,
                        exists_x_nnf=args.exists_x_nnf,
                    )
                )

            case 'sdd':
                sdd(
                    ArgumentsWithSDD(
                        mapping=mapping,
                        vtree=args.vtree,
                        sdd=args.sdd,
                        exists_x_vtree=args.exists_x_vtree,
                        exists_x_sdd=args.exists_x_sdd,
                    )
                )


if __name__ == '__main__':
    main()
