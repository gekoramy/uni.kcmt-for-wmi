import itertools as it
import logging
import os.path
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

from math import prod
from tqdm import tqdm

handler: logging.Handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s :: %(levelname)-4s :: %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(handler)

if __name__ == '__main__':
    wdr: Path = Path(__file__).parent.parent.parent
    src: Path = wdr / 'src'
    rsc: Path = wdr / 'resources'

    results: Path = rsc / 'results'
    results.mkdir(exist_ok=True)

    enumerators: list[str] = ['sae', 'd4', 'cudd']
    integrators: list[str] = ['noop']
    densities: list[Path] = list((rsc / 'densities').rglob('*.json', recurse_symlinks=True))

    with tqdm(
            iterable=it.product(enumerators, integrators, densities),
            total=prod(map(len, (enumerators, integrators, densities))),
            ascii=' ⠁⠃⠇⠏⠟⠯⠷⠿⡿⣟⣯⣷⣾⣿',
            bar_format='{bar} {n_fmt}/{total_fmt} {elapsed}/{remaining}',
    ) as todo:

        for enumerator, integrator, density in todo:

            if 0 == os.path.getsize(density):
                logger.warning(f'skipping {density}')
                continue

            # todo.set_postfix({'e': enumerator, 'i': integrator, 'd': density.name})

            path_err = results / f'{enumerator}-{integrator}-{density.name}-stderr.ndjson'
            path_out = results / f'{enumerator}-{integrator}-{density.name}-stdout.ndjson'

            with (
                open(path_out, 'wt') as out,
                open(path_err, 'wt') as err,
            ):
                try:
                    wmi: CompletedProcess[str] = (
                        subprocess.run(
                            [
                                'python',
                                '-m',
                                'src.wmi',
                                f'--density={density.as_posix()}',
                                f'--enumerator={enumerator}',
                                f'--integrator={integrator}'
                            ],
                            cwd=wdr,
                            text=True,
                            timeout=timedelta(minutes=1).total_seconds(),
                            stdout=out,
                            stderr=err,
                        )
                    )

                except TimeoutExpired as e:
                    logger.warning(f'{enumerator} {integrator} {density} timed out')

            if 0 != wmi.returncode:
                path_err.rename(path_err.parent / f'{enumerator}-{integrator}-{density.name}-stderr.log')
                path_out.rename(path_out.parent / f'{enumerator}-{integrator}-{density.name}-stdout.log')
                logger.error(f'{enumerator} {integrator} {density} non-zero exit')
                path_err.touch()
                path_out.touch()
