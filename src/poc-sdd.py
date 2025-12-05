# %%
import json
from io import StringIO
from subprocess import Popen
import re

import pysmt.shortcuts as s
import subprocess

from pathlib import Path

from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser

from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from theorydd.tdd.theory_sdd import TheorySDD

from src.sdd2nnf import main as sdd2nnf
from src.nnf2dot import main as nnf2dot

# %%
cwd = Path('.')

# %%
a = s.Symbol('a', s.BOOL)
x = s.Symbol('x', s.REAL)
y = s.Symbol('y', s.REAL)
z = s.Symbol('z', s.REAL)

phi: FNode = s.And(
    s.Implies(
        s.LT(x, y),
        s.LE(s.Plus(x, z), s.Real(0)),
    ),
    s.Or(s.LE(s.Real(-10), z), s.LT(y, z)),
    s.Iff(
        s.LT(x, y),
        s.LT(z, y),
    ),
    s.Iff(
        a,
        s.LT(z, y),
    ),
)

# %%
logger = {}

tsdd_folder = cwd / 'poc' / 'sdd'
tsdd_folder.mkdir(exist_ok=True)

tsdd = TheorySDD(
    phi,
    vtree_type='balanced',
    computation_logger=logger,
    solver=MathSATExtendedPartialEnumerator(),
)

tsdd.save_to_folder(tsdd_folder.as_posix())
tsdd.graphic_dump((tsdd_folder / 'sdd.svg').as_posix())
print(logger)

# %%
parser: SmtLibParser = SmtLibParser()

with open(tsdd_folder / 'abstraction.json', 'rt') as f:
    abs2theory: dict[int, FNode] = {
        l: parser.get_script(StringIO(formula)).get_last_formula()
        for formula, l in json.load(f)
    }

# %%
sdd2nnf(
    tsdd_folder / "sdd.sdd",
    tsdd_folder / "sdd.nff",
)

# %%
nnf2dot(
    tsdd_folder / "sdd.nff",
    tsdd_folder / "sdd.nff.dot",
)

# %%
decdnnf: Popen[str] = subprocess.Popen(
    args=[
        'decdnnf_rs',
        'model-enumeration',
        '--compact-free-vars',
        '--logging-level=off',
        f'--input={(tsdd_folder / "sdd.nff").as_posix()}'
    ],
    cwd=cwd,
    stdout=subprocess.PIPE,
    text=True,
)

b2regex: dict[bool, re.Pattern] = {
    False: re.compile(r'-(\d+)'),
    True: re.compile(r' (\d+)'),
}

for line in decdnnf.stdout:
    model: str = line.strip().removesuffix('0')

    print({
        boolean: [abs2theory[int(l)] for l in regex.findall(model)]
        for boolean, regex in b2regex.items()
    })

decdnnf.poll()
print(decdnnf.returncode)
