import argparse
import shutil
import subprocess
import tempfile
import typing
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

import pysmt.environment
import pysmt.shortcuts as smt
from array import array
from pysdd.sdd import SddManager, Vtree, SddNode
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import nnf_to_bcs12
from src import utils
from src.tddnnf import tlemmas


@dataclass(frozen=True)
class ArgumentsWithSDD:
    mapping: dict[int, FNode]
    project_onto: list[int]
    vtree: Path
    sdd: Path
    projected_vtree: Path
    projected_sdd: Path


@dataclass(frozen=True)
class ArgumentsWithD4:
    mapping: dict[int, FNode]
    project_onto: list[int]
    nnf: Path
    projected_nnf: Path


def d4(args: ArgumentsWithD4):
    match len(args.project_onto):
        case 0:
            with open(args.projected_nnf, 'wt') as fw:
                fw.writelines(
                    part
                    for line in ['t 1 0']
                    for part in [line, '\n']
                )

        case n if n == len(args.mapping):
            shutil.copyfile(args.nnf, args.projected_nnf)

        case _:
            with tempfile.TemporaryDirectory() as path:
                folder: Path = Path(path)

                projected_bc: Path = folder / 'projected.bc'
                projected_to_fix: Path = folder / 'projected.nnf'

                with utils.log('nnf -> BC-S1.2'):
                    nnf_to_bcs12.translate(
                        nnf=args.nnf,
                        project=args.project_onto,
                        bcs12=projected_bc,
                    )

                with utils.log('projecting'):
                    process: CompletedProcess[str] = subprocess.run(
                        [
                            'd4',
                            '--input', projected_bc,
                            '--input-type', 'circuit',
                            '--remove-gates', '1',
                            '--dump-file', projected_to_fix,
                        ],
                        capture_output=True,
                        text=True,
                    )

                    assert 0 == process.returncode, '\n'.join((process.stdout, process.stderr))

                with utils.log('fix nnf'), open(projected_to_fix, 'rt') as fr, open(args.projected_nnf, 'wt') as fw:
                    fw.writelines(
                        nnf_to_bcs12.fix_nnf(line)
                        for line in fr
                    )


def sdd(args: ArgumentsWithSDD):
    match len(args.project_onto):
        case 0:
            shutil.copyfile(args.vtree, args.projected_vtree)
            with open(args.projected_sdd, 'wt') as fw:
                fw.writelines(
                    part
                    for line in ['sdd 1', 'T 0']
                    for part in [line, '\n']
                )

        case n if n == len(args.mapping):
            shutil.copyfile(args.vtree, args.projected_vtree)
            shutil.copyfile(args.sdd, args.projected_sdd)

        case _:
            with utils.log('load vtree'):
                vtree: Vtree = Vtree.from_file(str.encode(args.vtree.as_posix()))
                mgr: SddManager = SddManager.from_vtree(vtree)

            with utils.log('load sdd'):
                phi: SddNode = mgr.read_sdd_file(str.encode(args.sdd.as_posix()))

            with utils.log('projecting'):
                which: list[int] = [1] * (1 + len(args.mapping))
                for k in args.project_onto:
                    which[k] = 0

                projected_phi: SddNode = mgr.exists_multiple(array('i', which), phi)

            with utils.log('store'):
                vtree.save(str.encode(args.projected_vtree.as_posix()))
                projected_phi.save(str.encode(args.projected_sdd.as_posix()))


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--steps', type=Path, required=True)
        parser.add_argument('--mapping', type=utils.file, required=True)
        parser.add_argument('--quantify_out', type=str, choices=['x', 'A'], required=True)

        with utils.use(parser.add_subparsers(dest='compiler', required=True)) as sub:
            with utils.use(sub.add_parser('d4')) as subparser:
                subparser.add_argument('--nnf', type=utils.file, required=True)
                subparser.add_argument('--projected_nnf', type=Path, required=True)

            with utils.use(sub.add_parser('sdd')) as subparser:
                subparser.add_argument('--vtree', type=utils.file, required=True)
                subparser.add_argument('--sdd', type=utils.file, required=True)
                subparser.add_argument('--projected_vtree', type=Path, required=True)
                subparser.add_argument('--projected_sdd', type=Path, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    with utils.log('total'):

        env: Environment = pysmt.environment.get_env()
        mapping: dict[int, FNode] = tlemmas.read_mapping(env=env, mapping=args.mapping)

        to_project_onto: typing.Callable[[FNode], bool]
        match args.quantify_out:
            case 'x':
                to_project_onto = lambda fnode: fnode.is_symbol(smt.BOOL)

            case 'A':
                to_project_onto = lambda fnode: not fnode.is_symbol(smt.BOOL)

        project_onto: list[int] = [k for k, v in mapping.items() if to_project_onto(v)]

        match args.compiler:
            case 'd4':
                d4(
                    ArgumentsWithD4(
                        mapping=mapping,
                        project_onto=project_onto,
                        nnf=args.nnf,
                        projected_nnf=args.projected_nnf,
                    )
                )

            case 'sdd':
                sdd(
                    ArgumentsWithSDD(
                        mapping=mapping,
                        project_onto=project_onto,
                        vtree=args.vtree,
                        sdd=args.sdd,
                        projected_vtree=args.projected_vtree,
                        projected_sdd=args.projected_sdd,
                    )
                )


if __name__ == '__main__':
    main()
