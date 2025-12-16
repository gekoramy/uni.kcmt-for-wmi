import itertools as it
import logging
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess

from math import prod
from tqdm import tqdm

# %%
handler: logging.Handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s :: %(levelname)-4s :: %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(handler)

# %%
wdr: Path = Path(__file__).parent.parent.parent
out: Path = wdr / 'resources' / 'densities' / 'synthetic-2.0'
out.mkdir(exist_ok=True)

seeds: list[int] = [2, 79, 191, 311, 439]
reals: list[int] = [3, 5]
bools: list[int] = [3, 5]
clauses: list[int] = [9, 13]
literals: list[int] = [7]
p_bools: list[float] = [.5, .6]

# %%
with tqdm(
        iterable=it.product(seeds, reals, bools, clauses, literals, p_bools),
        total=prod(map(len, (seeds, reals, bools, clauses, literals, p_bools))),
        ascii=' ⠁⠃⠇⠏⠟⠯⠷⠿⡿⣟⣯⣷⣾⣿',
        bar_format='{bar} {n_fmt}/{total_fmt} {elapsed}/{remaining}',
) as todo:
    for s, r, b, c, l, p in todo:

        process: CompletedProcess[str] = subprocess.run(
            [
                'python',
                wdr / 'wmpy' / 'benchmarks' / 'synthetic.py',
                str(s),
                f'--n_reals={r}',
                f'--n_bools={b}',
                f'--n_clauses={c}',
                f'--len_clauses={l}',
                f'--p_bool={p}',
            ],
            capture_output=True,
            text=True,
            cwd=out,
        )

        if 0 != process.returncode:
            logger.error(process.args)
