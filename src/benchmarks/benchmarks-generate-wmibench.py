# %%
import dataclasses
import subprocess
import typing as t
from pathlib import Path
from subprocess import CompletedProcess


# %%
@dataclasses.dataclass
class Wrap:
    what: t.Any

    def __enter__(self):
        return self.what

    def __exit__(self, *_):
        del self


# %%
image: str = 'wmibench'
cwd: Path = Path(__file__).parent
seed: int = 17
base: list[str] = [
    'docker',
    'run',
    '--entrypoint=python',
    '--rm',
    f'-v={(cwd.parent.parent.parent / "resources" / "densities").as_posix()}:/workdir',
    '-w=/workdir',
    image
]

# %%
assert (
        0 == subprocess.run(['docker', 'image', 'inspect', image]).returncode
        or
        0 == subprocess.run(['docker', 'build', f'-f={(cwd / "Dockerfile").as_posix()}', f'-t={image}', '.']).returncode
)

# %%
p4where: CompletedProcess[str] = subprocess.run(
    base + ['-c', 'from distutils.sysconfig import get_python_lib; print(get_python_lib())'],
    capture_output=True,
    text=True,
)

assert 0 == p4where.returncode == len(p4where.stderr)

where: Path = Path(p4where.stdout.strip()) / 'wmibench'

# %%
with Wrap(subprocess.run(base + [where / 'synthetic' / 'synthetic_pa.py', f'-s={seed}'])) as p:
    print(p)
    assert 0 == p.returncode

# %%
for type in [
    # 'xor',
    # 'mutex',
    # 'click',
    'uni',
    'dual',
    'dual_paths',
    'dual_paths_distinct',
    'and_overlap',
    'tpg_star',
    'tpg_3ary_tree',
    'tpg_path'
]:
    for size in [37, 73]:
        with Wrap(subprocess.run(base + [where / 'synthetic' / 'synthetic_structured.py', f'-s={seed}', type, str(size)])) as p:
            print(p)
            # assert 0 == p.returncode
