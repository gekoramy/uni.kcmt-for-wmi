import argparse
import functools as ft
import gzip
import itertools as it
import tempfile
from multiprocessing.pool import Pool
from pathlib import Path

from pysdd.sdd import SddManager, Vtree, SddNode

from src import condition
from src import minimize_nnf
from src import sdd_to_nnf
from src import utils
from src.decdnnf import decdnnf


def conditioning_nnf(
        nnf: Path,
        mu_projected: dict[bool, list[int]],
) -> list[dict[bool, list[int]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)
        conditioned: Path = folder / 'conditioned.nnf'

        with open(nnf, 'r', encoding='utf-8') as f:
            unoptimized: list[str] = condition.conditioning(
                raw=f,
                assumptions=frozenset(it.chain(
                    mu_projected[True],
                    (-l for l in mu_projected[False])
                )),
            )

        minimize(unoptimized, conditioned)

        return enumerate_models(mu_projected, conditioned)


def conditioning_sdd(
        vtree: Path,
        sdd: Path,
        mu_projected: dict[bool, list[int]],
) -> list[dict[bool, list[int]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        vtree_obj: Vtree = Vtree.from_file(str.encode(vtree.as_posix()))
        mgr: SddManager = SddManager.from_vtree(vtree_obj)
        root: SddNode = mgr.read_sdd_file(str.encode(sdd.as_posix()))

        root = ft.reduce(
            lambda acc, l: mgr.condition(l, acc),
            it.chain(
                mu_projected[True],
                (-l for l in mu_projected[False])
            ),
            root,
        )

        root.ref()
        mgr.minimize_limited()

        sdd_path: Path = folder / 'sdd.sdd'
        nnf: Path = folder / 'sdd.nnf'

        root.save(str.encode(sdd_path.as_posix()))

        with open(sdd_path, 'r', encoding='utf-8') as f:
            unoptimized: list[str] = sdd_to_nnf.sdd2nnf(f)

        minimize(unoptimized, nnf)

        return enumerate_models(mu_projected, nnf)


def minimize(definition: list[str], nnf: Path) -> None:
    with open(nnf, 'w', encoding='utf-8') as f:
        f.writelines(
            part
            for line in minimize_nnf.minimizing((line + ' 0' for line in definition))
            for part in (line, ' 0\n')
        )


def enumerate_models(mu_projected: dict[bool, list[int]], nnf: Path) -> list[dict[bool, list[int]]]:
    return [
        {
            boolean: mu_projected[boolean] + literals
            for boolean, literals in mu_conditioned.items()
        }
        for mu_conditioned in decdnnf.raw(cores=1, nnf=nnf)
    ]


def process_with_nnf(
        cores: int,
        mus_projected: list[dict[bool, list[int]]],
        nnf: Path,
) -> list[list[dict[bool, list[int]]]]:
    with Pool(cores) as pool:
        return pool.starmap(
            conditioning_nnf,
            zip(
                it.cycle([nnf]),
                mus_projected,
            )
        )


def process_with_sdd(
        cores: int,
        mus_projected: list[dict[bool, list[int]]],
        vtree: Path,
        sdd: Path,
) -> list[list[dict[bool, list[int]]]]:
    with Pool(cores) as pool:
        return pool.starmap(
            conditioning_sdd,
            zip(
                it.cycle([vtree]),
                it.cycle([sdd]),
                mus_projected,
            )
        )


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--models_projected', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)

        with utils.use(parser.add_subparsers(dest='kind', required=True)) as sub:
            with utils.use(sub.add_parser('nnf')) as subparser:
                subparser.add_argument('--nnf', type=utils.file, required=True)

            with utils.use(sub.add_parser('sdd')) as subparser:
                subparser.add_argument('--vtree', type=utils.file, required=True)
                subparser.add_argument('--sdd', type=utils.file, required=True)

        args: argparse.Namespace = parser.parse_args()

    with gzip.open(args.models_projected, 'rt', encoding='utf-8') as f:
        mus_projected: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    models: list[list[dict[bool, list[int]]]]
    match args.kind:
        case 'nnf':
            models = process_with_nnf(
                cores=args.cores,
                mus_projected=mus_projected,
                nnf=args.nnf,
            )

        case 'sdd':
            models = process_with_sdd(
                cores=args.cores,
                mus_projected=mus_projected,
                vtree=args.vtree,
                sdd=args.sdd,
            )

    decdnnf.write_models(args.output, it.chain(*models))


if __name__ == '__main__':
    main()
