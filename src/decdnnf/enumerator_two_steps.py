import functools as ft
import itertools as it
import tempfile
import typing as t
from dataclasses import dataclass
from multiprocessing.pool import Pool
from pathlib import Path

from pysdd.sdd import SddManager, Vtree, SddNode
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import condition
from src import minimize_nnf
from src import sdd_to_nnf
from src import tddnnf
from src import utils
from src.decdnnf import decdnnf


@dataclass(frozen=True)
class Arguments:
    cores: int
    nnf_projected: Path
    mapping: Path
    nnf: Path


@dataclass(frozen=True)
class ArgumentsWithSDD:
    cores: int
    nnf_projected: Path
    mapping: Path
    vtree: Path
    sdd: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: dict[int, FNode] = tddnnf.mapping(env, args.mapping)
        mus_projected: t.Generator[dict[bool, list[int]]] = decdnnf.raw(nnf=args.nnf_projected, cores=args.cores)

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[int]]]] = pool.starmap(
                conditioning,
                zip(
                    it.cycle([args.nnf]),
                    mus_projected,
                )
            )

        yield from (
            {
                boolean: [mapping[l] for l in literals]
                for boolean, literals in model.items()
            }
            for model in it.chain(*models)
        )


def enum_with_sdd(
        env: Environment,
        args: ArgumentsWithSDD,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: dict[int, FNode] = tddnnf.mapping(env, args.mapping)
        mus_projected: t.Generator[dict[bool, list[int]]] = decdnnf.raw(nnf=args.nnf_projected, cores=args.cores)

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[int]]]] = pool.starmap(
                conditioning_with_sdd,
                zip(
                    it.cycle([args.vtree]),
                    it.cycle([args.sdd]),
                    mus_projected,
                )
            )

        yield from (
            {
                boolean: [mapping[l] for l in literals]
                for boolean, literals in model.items()
            }
            for model in it.chain(*models)
        )


def conditioning(
        nnf: Path,
        mu_projected: dict[bool, list[int]],
) -> list[dict[bool, list[int]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)
        conditioned: Path = folder / 'conditioned.nnf'

        with open(nnf, 'rt') as f:
            unoptimized: list[str] = condition.conditioning(
                raw=f,
                assumptions=frozenset(it.chain(
                    mu_projected[True],
                    (-l for l in mu_projected[False])
                )),
            )

        with open(conditioned, 'wt') as f:
            f.writelines(
                part
                for line in minimize_nnf.minimizing((line + ' 0' for line in unoptimized))
                for part in (line, ' 0\n')
            )

        return [
            {
                boolean: mu_projected[boolean] + literals
                for boolean, literals in mu_conditioned.items()
            }
            for mu_conditioned in decdnnf.raw(cores=1, nnf=conditioned)
        ]


def conditioning_with_sdd(
        vtree: Path,
        sdd: Path,
        mu_projected: dict[bool, list[int]],
) -> list[dict[bool, list[int]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        vtree: Vtree = Vtree.from_file(str.encode(vtree.as_posix()))
        mgr: SddManager = SddManager.from_vtree(vtree)
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

        sdd: Path = folder / 'sdd.sdd'
        nnf: Path = folder / 'sdd.nnf'

        root.save(str.encode(sdd.as_posix()))

        with open(sdd, 'rt') as f:
            unoptimized: list[str] = sdd_to_nnf.sdd2nnf(f)

        with open(nnf, 'wt') as f:
            f.writelines(
                part
                for line in minimize_nnf.minimizing((line + ' 0' for line in unoptimized))
                for part in (line, ' 0\n')
            )

        return [
            {
                boolean: mu_projected[boolean] + literals
                for boolean, literals in mu_conditioned.items()
            }
            for mu_conditioned in decdnnf.raw(cores=1, nnf=nnf)
        ]
