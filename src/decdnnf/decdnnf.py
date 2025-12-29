import json
import re
import subprocess
import typing as t
from io import StringIO
from pathlib import Path

from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser

from src import utils

b2regex: frozenset[tuple[bool, re.Pattern]] = frozenset([
    (False, re.compile(r'-(\d+)')),
    (True, re.compile(r' (\d+)')),
])


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


def raw(
        cores: int,
        nnf: Path,
) -> t.Generator[dict[bool, list[int]]]:
    with utils.log('decdnnf_rs'):
        decdnnf: subprocess.CompletedProcess[str] = subprocess.run(
            args=[
                'decdnnf_rs',
                'model-enumeration',
                '--compact-free-vars',
                '--logging-level', 'off',
                '--input', nnf.as_posix(),
                *(
                    ['--threads', str(cores)]
                    if cores > 1
                    else []
                )
            ],
            text=True,
            capture_output=True,
        )

    assert 0 == decdnnf.returncode, decdnnf.stdout

    yield from (
        {
            boolean: [int(l) for l in regex.findall(line.strip().removesuffix('0'))]
            for boolean, regex in b2regex
        }
        for line in decdnnf.stdout.splitlines()
    )


def convert(
        mapping: dict[int, FNode],
        mu: dict[bool, list[int]],
) -> dict[bool, list[FNode]]:
    return {
        boolean: [mapping[l] for l in literals]
        for boolean, literals in mu
    }
