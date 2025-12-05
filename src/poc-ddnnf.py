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
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF

from nnf2dot import main as nnf2dot

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

ddnnf_folder: Path = cwd / 'poc' / 'ddnnf'
ddnnf_folder.mkdir(exist_ok=True)

tddnnf = TheoryDDNNF(
    phi,
    computation_logger=logger,
    solver=MathSATExtendedPartialEnumerator(),
    base_out_path=ddnnf_folder.as_posix(),
    parallel_allsmt_procs=2,
    store_tlemmas=True,
    stop_after_allsmt=False,
)

print(logger)

# %%
parser: SmtLibParser = SmtLibParser()

with open(ddnnf_folder / 'mapping' / 'mapping.json', 'rt') as f:
    abs2theory: dict[int, FNode] = {
        l: parser.get_script(StringIO(formula)).get_last_formula()
        for l, formula in json.load(f)
    }

# %%
nnf2dot(
    ddnnf_folder / 'compilation_output.nnf',
    ddnnf_folder / 'nnf.dot'
)

# %%
decdnnf: Popen[str] = subprocess.Popen(
    args=[
        'decdnnf_rs',
        'model-enumeration',
        '--compact-free-vars',
        '--logging-level=off',
        f'--input={(ddnnf_folder / 'compilation_output.nnf').as_posix()}'
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
