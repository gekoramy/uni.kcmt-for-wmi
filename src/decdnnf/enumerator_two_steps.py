import functools as ft
import itertools as it
import tempfile
import typing as t
from dataclasses import dataclass
from multiprocessing.pool import Pool
from pathlib import Path

import pysmt.shortcuts as smt
from pysdd.sdd import SddManager, Vtree, SddNode
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import condition
from src import minimize_nnf
from src import sdd_to_nnf
from src import utils
from src.decdnnf import decdnnf
from src.tddnnf import tlemmas


@dataclass(frozen=True)
class Arguments:
    cores: int
    quantify_out: t.Literal['x', 'A']
    models_projected: Path
    mapping: Path
    nnf: Path


@dataclass(frozen=True)
class ArgumentsWithSDD:
    cores: int
    quantify_out: t.Literal['x', 'A']
    models_projected: Path
    mapping: Path
    vtree: Path
    sdd: Path


def inspect(
        mapping: tlemmas.i2atom,
        quantify_out: t.Literal['x', 'A'],
        mus_projected: list[dict[bool, list[int]]],
        modelss: list[list[dict[bool, list[int]]]],
) -> None:
    quantified_out: t.Callable[[FNode], bool]
    match quantify_out:
        case 'x':
            quantified_out = lambda fnode: not fnode.is_symbol(smt.BOOL)

        case 'A':
            quantified_out = lambda fnode: fnode.is_symbol(smt.BOOL)

    rem: frozenset[int] = frozenset(
        i
        for i, atom in tlemmas.entries(mapping)
        if not quantified_out(atom)
    )

    utils.log_entry(
        "distinct",
        len(set(
            frozenset(
                [
                    *model[True],
                    *(-atom for atom in model[False])
                ]
            )
            for models in modelss
            for model in models
        ))
    )

    utils.log_entry(
        "models'",
        sum(
            any(
                i in rem_prime
                for i in it.chain(*model.values())
            )
            for mu_projected, models in zip(mus_projected, modelss)
            if (rem_prime := rem.difference(it.chain(*mu_projected.values())))
            for model in models
        )
    )


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: tlemmas.i2atom = tlemmas.read_mapping(env, args.mapping)

        with open(args.models_projected, 'r', encoding='utf-8') as f:
            mus_projected: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[int]]]] = pool.starmap(
                conditioning,
                zip(
                    it.cycle([args.nnf]),
                    mus_projected,
                )
            )

        inspect(
            mapping,
            args.quantify_out,
            mus_projected,
            models,
        )

        yield from (
            tlemmas.convert(mapping, model)
            for model in it.chain(*models)
        )


def enum_with_sdd(
        env: Environment,
        args: ArgumentsWithSDD,
) -> t.Generator[dict[bool, list[FNode]]]:
    with utils.log('two steps'):
        mapping: tlemmas.i2atom = tlemmas.read_mapping(env, args.mapping)

        with open(args.models_projected, 'r', encoding='utf-8') as f:
            mus_projected: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

        with Pool(args.cores) as pool:
            models: list[list[dict[bool, list[int]]]] = pool.starmap(
                conditioning_with_sdd,
                zip(
                    it.cycle([args.vtree]),
                    it.cycle([args.sdd]),
                    mus_projected,
                )
            )

        inspect(
            mapping,
            args.quantify_out,
            mus_projected,
            models,
        )

        yield from (
            tlemmas.convert(mapping, model)
            for model in it.chain(*models)
        )


def conditioning(
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

        return mus(mu_projected, conditioned)


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

        with open(sdd, 'r', encoding='utf-8') as f:
            unoptimized: list[str] = sdd_to_nnf.sdd2nnf(f)

        minimize(unoptimized, nnf)

        return mus(mu_projected, nnf)


def minimize(definition: list[str], nnf: Path) -> None:
    with open(nnf, 'w', encoding='utf-8') as f:
        f.writelines(
            part
            for line in minimize_nnf.minimizing((line + ' 0' for line in definition))
            for part in (line, ' 0\n')
        )


def mus(mu_projected: dict[bool, list[int]], nnf: Path) -> list[dict[bool, list[int]]]:
    return [
        {
            boolean: mu_projected[boolean] + literals
            for boolean, literals in mu_conditioned.items()
        }
        for mu_conditioned in decdnnf.raw(cores=1, nnf=nnf)
    ]
