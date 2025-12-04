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
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF

# %%
cwd = Path('.')

# %%
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

for line in decdnnf.stdout:

    model = line.strip().removesuffix('0')

    P = list(map(int, re.findall(r' (\d+)', model)))
    N = list(map(int, re.findall(r'-(\d+)', model)))

    print(
        [abs2theory.get(l, l) for l in P],
        [abs2theory.get(l, l) for l in N],
    )

decdnnf.poll()
print(decdnnf.returncode)
