import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pysmt.shortcuts as smt
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from theorydd.tdd.theory_sdd import TheorySDD
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF
from wmpy.cli.density import Density

from src import utils


@dataclass(frozen=True)
class ArgumentsWithSDD:
    cores: int
    phi: FNode
    tlemmas: Path
    mapping: Path
    vtree: Path
    sdd: Path


@dataclass(frozen=True)
class ArgumentsWithD4:
    cores: int
    phi: FNode
    tlemmas: Path
    mapping: Path
    nnf: Path


def mapping(
        env: Environment,
        mapping: Path
) -> dict[int, FNode]:
    with utils.log('parsing abstraction'), open(mapping, 'rt') as f:
        parser: SmtLibParser = SmtLibParser(environment=env)

        return {
            k: parser.get_script(StringIO(v)).get_last_formula()
            for k, v in json.load(f)
        }


def convert(
        mapping: dict[int, FNode],
        mu: dict[bool, list[int]],
) -> dict[bool, list[FNode]]:
    return {
        boolean: [mapping[l] for l in literals]
        for boolean, literals in mu.items()
    }


def sdd(args: ArgumentsWithSDD) -> None:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        with utils.log('pysmt -> t-SDD'), utils.computations() as computations:
            tddnnf: TheorySDD = TheorySDD(
                args.phi,
                load_lemmas=args.tlemmas.as_posix(),
                vtree_type='balanced',
                computation_logger=computations,
                solver=MathSATExtendedPartialEnumerator(
                    computation_logger=computations,
                    parallel_procs=args.cores,
                ),
            )

        with utils.log('export sdd'):
            tddnnf.save_to_folder(folder.as_posix())

        with utils.log('fix mapping.json'), open(folder / 'abstraction.json') as I, open(args.mapping, 'wt') as O:
            json.dump([(k, v) for v, k in json.load(I)], O)

        with utils.log('export'):
            shutil.move(folder / 'sdd.sdd', args.sdd)
            shutil.move(folder / 'vtree.vtree', args.vtree)


def d4(args: ArgumentsWithD4) -> None:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        with utils.log('pysmt -> t-d-DNNF'), utils.computations() as computations:
            TheoryDDNNF(
                args.phi,
                load_lemmas=args.tlemmas.as_posix(),
                sat_result=True,
                base_out_path=folder.as_posix(),
                store_tlemmas=True,
                stop_after_allsmt=False,
                computation_logger=computations,
                solver=MathSATExtendedPartialEnumerator(
                    computation_logger=computations,
                    parallel_procs=args.cores,
                ),
            )

        with utils.log('export'):
            shutil.move(folder / 'mapping' / 'mapping.json', args.mapping)
            shutil.move(folder / 'compilation_output.nnf', args.nnf)


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--steps', type=Path, required=True)
        parser.add_argument('--density', type=utils.file, required=True)
        parser.add_argument('--tlemmas', type=utils.file, required=True)
        parser.add_argument('--mapping', type=Path, required=True)

        with utils.use(parser.add_subparsers(dest='compiler', required=True)) as sub:
            with utils.use(sub.add_parser('d4')) as subparser:
                subparser.add_argument('--nnf', type=Path, required=True)

            with utils.use(sub.add_parser('sdd')) as subparser:
                subparser.add_argument('--vtree', type=Path, required=True)
                subparser.add_argument('--sdd', type=Path, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    density: Density = utils.read_density(args.density)
    formula: FNode = smt.And(density.support, smt.Bool(True))

    with utils.log('total'):
        match args.compiler:
            case 'd4':
                d4(
                    ArgumentsWithD4(
                        cores=args.cores,
                        phi=formula,
                        tlemmas=args.tlemmas,
                        mapping=args.mapping,
                        nnf=args.nnf,
                    )
                )

            case 'sdd':
                sdd(
                    ArgumentsWithSDD(
                        cores=args.cores,
                        phi=formula,
                        tlemmas=args.tlemmas,
                        mapping=args.mapping,
                        vtree=args.vtree,
                        sdd=args.sdd,
                    )
                )


if __name__ == '__main__':
    main()
