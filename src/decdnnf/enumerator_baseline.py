import typing as t
from dataclasses import dataclass

from matplotlib.path import Path
from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import tddnnf
from src.decdnnf import decdnnf


@dataclass(frozen=True)
class Arguments:
    cores: int
    nnf: Path
    mapping: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    mapping: dict[int, FNode] = tddnnf.mapping(env, args.mapping)

    yield from (
        {
            boolean: [mapping[l] for l in literals]
            for boolean, literals in mu.items()
        }
        for mu in decdnnf.raw(cores=args.cores, nnf=args.nnf)
    )
