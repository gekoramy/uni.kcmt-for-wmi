# %%
import pysmt.shortcuts as s

from pathlib import Path
from theorydd.abstractdd.abstraction_sdd import AbstractionSDD
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF

# %%
cwd = Path('.')

# %%
x = s.Symbol('x', s.REAL)
y = s.Symbol('y', s.REAL)
z = s.Symbol('z', s.REAL)

phi = s.And(
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

sdd = AbstractionSDD(
    phi,
    vtree_type='balanced',
    solver='partial',
    computation_logger=logger,
)

sdd_folder = cwd / 'poc' / 'sdd'

sdd.save_to_folder(sdd_folder.as_posix())
sdd.graphic_dump((sdd_folder / 'sdd.svg').as_posix())
print(logger)

# %%
logger = {}
ddnnf_folder: Path = cwd / 'poc' / 'ddnnf'

tddnnf = TheoryDDNNF(
    phi,
    computation_logger=logger,
    base_out_path=ddnnf_folder.as_posix(),
    parallel_allsmt_procs=2,
    store_tlemmas=True,
    stop_after_allsmt=False,
    solver=MathSATExtendedPartialEnumerator(),
)

print(logger)
