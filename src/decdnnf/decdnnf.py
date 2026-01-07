import re
import subprocess
import typing as t
from pathlib import Path

from src import utils

b2regex: frozenset[tuple[bool, re.Pattern]] = frozenset([
    (False, re.compile(r'-(\d+)')),
    (True, re.compile(r' (\d+)')),
])


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

    yield from parse(decdnnf.stdout.splitlines())


def parse(
        lines: t.Iterable[str]
) -> t.Generator[dict[bool, list[int]]]:
    yield from (
        {
            boolean: [int(l) for l in regex.findall(line.strip().removesuffix('0'))]
            for boolean, regex in b2regex
        }
        for line in lines
    )
