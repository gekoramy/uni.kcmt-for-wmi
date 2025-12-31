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

from src import utils
from src.condition import condition
from src.decdnnf import decdnnf
from src.sdd2nnf import main as sdd2nnf


@dataclass(frozen=True)
class Arguments:
    cores: int
    nnf_exists_x: Path
    mapping: Path
    nnf: Path


@dataclass(frozen=True)
class ArgumentsWithSDD:
    cores: int
    nnf_exists_x: Path
    mapping: Path
    vtree: Path
    sdd: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: dict[int, FNode] = decdnnf.mapping(env, args.mapping)
        mu_exists_x: t.Generator[dict[bool, list[int]]] = decdnnf.raw(nnf=args.nnf_exists_x, cores=args.cores)

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[FNode]]]] = pool.starmap(
                conditioning,
                zip(
                    it.cycle([args.nnf]),
                    it.cycle([mapping]),
                    mu_exists_x,
                )
            )

        yield from it.chain(*models)


def enum_with_sdd(
        env: Environment,
        args: ArgumentsWithSDD,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: dict[int, FNode] = decdnnf.mapping(env, args.mapping)
        mu_exists_x: t.Generator[dict[bool, list[int]]] = decdnnf.raw(nnf=args.nnf_exists_x, cores=args.cores)

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[FNode]]]] = pool.starmap(
                conditioning_with_sdd,
                zip(
                    it.cycle([args.vtree]),
                    it.cycle([args.sdd]),
                    it.cycle([mapping]),
                    mu_exists_x,
                )
            )

        yield from it.chain(*models)


def conditioning(
        nnf: Path,
        mapping: dict[int, FNode],
        mu_exists_x: dict[bool, list[int]],
) -> list[dict[bool, list[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)
        conditioned: Path = folder / 'conditioned.nnf'

        condition(
            nnf=nnf,
            assumptions=frozenset(it.chain(
                mu_exists_x[True],
                (-l for l in mu_exists_x[False])
            )),
            conditioned=conditioned,
        )

        return [
            {
                boolean: [mapping[l] for l in mu_exists_x[boolean] + literals]
                for boolean, literals in mu_conditioned.items()
            }
            for mu_conditioned in decdnnf.raw(cores=1, nnf=conditioned)
        ]


def conditioning_with_sdd(
        vtree: Path,
        sdd: Path,
        mapping: dict[int, FNode],
        mu_exists_x: dict[bool, list[int]],
) -> list[dict[bool, list[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder = Path(path)

        vtree: Vtree = Vtree.from_file(vtree.as_posix())
        mgr: SddManager = SddManager.from_vtree(vtree)
        root: SddNode = mgr.read_sdd_file(str.encode(sdd.as_posix()))

        root = ft.reduce(
            lambda acc, l: mgr.condition(l, acc),
            it.chain(
                mu_exists_x[True],
                (-l for l in mu_exists_x[False])
            ),
            root,
        )

        sdd: Path = folder / 'sdd.sdd'
        nnf: Path = folder / 'sdd.nnf'

        root.save(str.encode(sdd.as_posix()))
        sdd2nnf(sdd, nnf)

        return [
            {
                boolean: [mapping[l] for l in mu_exists_x[boolean] + literals]
                for boolean, literals in mu_conditioned.items()
            }
            for mu_conditioned in decdnnf.raw(cores=1, nnf=nnf)
        ]
