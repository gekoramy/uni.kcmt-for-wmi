import argparse
import shutil
import typing
from dataclasses import dataclass
from pathlib import Path

import pysmt.environment
import pysmt.shortcuts as smt
from array import array
from pysdd.sdd import SddManager, Vtree, SddNode
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import utils
from src.tddnnf import with_tlemmas


@dataclass(frozen=True)
class ArgumentsWithSDD:
    mapping: with_tlemmas.i2atom
    project_onto: list[int]
    vtree: Path
    sdd: Path
    projected_vtree: Path
    projected_sdd: Path


@dataclass(frozen=True)
class ArgumentsWithBCS12:
    mapping: with_tlemmas.i2atom
    project_onto: list[int]
    bcs12: Path
    projected_bcs12: Path


def bcs12(args: ArgumentsWithBCS12):
    match len(args.project_onto):
        case 0:
            raise NotImplementedError

        case n if n == with_tlemmas.atoms(args.mapping):
            shutil.copyfile(args.bcs12, args.projected_bcs12)

        case _:
            with utils.log('reading'), open(args.bcs12, 'r', encoding='utf-8') as f:
                lines: list[str] = f.readlines()

            assert 1 == sum(line.startswith('P') for line in lines)

            with utils.log('writing'), open(args.projected_bcs12, 'w', encoding='utf-8') as f:
                f.writelines(
                    f'P {' '.join(map(str, args.project_onto))}\n' if line.startswith('P') else line
                    for line in lines
                )


def sdd(args: ArgumentsWithSDD):
    match len(args.project_onto):
        case 0:
            raise NotImplementedError

        case n if n == with_tlemmas.atoms(args.mapping):
            shutil.copyfile(args.vtree, args.projected_vtree)
            shutil.copyfile(args.sdd, args.projected_sdd)

        case _:
            with utils.log('load vtree'):
                vtree: Vtree = Vtree.from_file(str.encode(args.vtree.as_posix()))
                mgr: SddManager = SddManager.from_vtree(vtree)

            with utils.log('load sdd'):
                phi: SddNode = mgr.read_sdd_file(str.encode(args.sdd.as_posix()))

            with utils.log('projecting'):
                which: list[int] = [1] * (1 + with_tlemmas.atoms(args.mapping))
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
            with utils.use(sub.add_parser('bcs12')) as subparser:
                subparser.add_argument('--bcs12', type=utils.file, required=True)
                subparser.add_argument('--projected_bcs12', type=Path, required=True)

            with utils.use(sub.add_parser('sdd')) as subparser:
                subparser.add_argument('--vtree', type=utils.file, required=True)
                subparser.add_argument('--sdd', type=utils.file, required=True)
                subparser.add_argument('--projected_vtree', type=Path, required=True)
                subparser.add_argument('--projected_sdd', type=Path, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    with utils.log('total'):

        env: Environment = pysmt.environment.get_env()
        mapping: with_tlemmas.i2atom = with_tlemmas.read_mapping(env=env, mapping=args.mapping)

        to_project_onto: typing.Callable[[FNode], bool]
        match args.quantify_out:
            case 'x':
                to_project_onto = lambda fnode: fnode.is_symbol(smt.BOOL)

            case 'A':
                to_project_onto = lambda fnode: not fnode.is_symbol(smt.BOOL)

        project_onto: list[int] = [k for k, v in with_tlemmas.entries(mapping) if to_project_onto(v)]

        match args.compiler:
            case 'bcs12':
                bcs12(
                    ArgumentsWithBCS12(
                        mapping=mapping,
                        project_onto=project_onto,
                        bcs12=args.bcs12,
                        projected_bcs12=args.projected_bcs12,
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
