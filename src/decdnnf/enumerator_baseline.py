import typing as t
from dataclasses import dataclass
from pathlib import Path

from pysmt.environment import Environment
from pysmt.fnode import FNode

from src import tddnnf
from src.decdnnf import decdnnf


@dataclass(frozen=True)
class Arguments:
    cores: int
    models: Path
    mapping: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    mapping: dict[int, FNode] = tddnnf.mapping(env, args.mapping)

    with open(args.models, 'rt') as f:
        mus: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    yield from (
        tddnnf.convert(mapping, mu)
        for mu in mus
    )
