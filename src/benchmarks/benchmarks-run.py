import itertools as it
import logging
import os.path
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

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

    enumerators = ['sae', 'd4', 'cudd']
    integrators = ['noop']
    densities = (rsc / 'densities').rglob('*.json', recurse_symlinks=True)

    for enumerator, integrator, density in it.product(enumerators, integrators, densities):

        if 0 == os.path.getsize(density):
            logger.warning(f'skipping {density}')
            continue

        logger.info(f"{enumerator} {integrator} {density.name}")

        with (
            open(results / f'{enumerator}-{integrator}-{density.name}-stdout.ndjson', 'wt') as out,
            open(results / f'{enumerator}-{integrator}-{density.name}-stderr.ndjson', 'wt') as err,
        ):
            try:
                wmi: CompletedProcess[str] = (
                    subprocess.run(
                        [
                            'python',
                            src / 'wmi.py',
                            f'--density={density.as_posix()}',
                            f'--enumerator={enumerator}',
                            f'--integrator={integrator}'
                        ],
                        text=True,
                        timeout=timedelta(minutes=1).total_seconds(),
                        stdout=out,
                        stderr=err,
                    )
                )

            except TimeoutExpired as e:
                logger.warning(f'{enumerator} {integrator} {density} timed out')
