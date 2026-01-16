import contextlib
import logging
import typing as t
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from time import perf_counter

from wmpy.cli.density import Density


@dataclass
class Log(contextlib.AbstractContextManager):
    logger: logging.Logger
    step: str

    def __enter__(self):
        self.start: float = perf_counter()

    def __exit__(self, *_):
        log_step(self.step, perf_counter() - self.start)


def logger() -> logging.Logger:
    return logging.getLogger(__file__)


def log(step: str) -> Log:
    return Log(logger(), step)


def setup(
        path: Path,
) -> None:
    path.touch()
    lgr: Logger = logger()
    lgr.setLevel(logging.DEBUG)
    lgr.propagate = False
    lgr.addHandler(logging.FileHandler(path))


def log_step(step: str, took: float) -> None:
    logger().debug('{"step": "%s", "took": %f}', step, took)


def log_entry(key: str, value: int) -> None:
    logger().debug('{"step": "%s", "took": %d}', key, value)


def times(whatever: dict[str, dict | float]) -> t.Iterable[tuple[str, float]]:
    """
    >>> list(times({ 'alpha time': 1.0, 'alpha': { 'beta time': 2.0, 'beta': { 'gamma time': 3.0 } } }))
    [('alpha time', 1.0), ('beta time', 2.0), ('gamma time', 3.0)]
    """

    for key, value in whatever.items():

        match value:
            case float() if 'time' in key:
                yield key, value

            case dict():
                yield from times(value)


def file(arg: str) -> Path:
    if not (path := Path(arg)).is_file():
        raise FileNotFoundError(path)

    return path


def read_density(path: Path) -> Density:
    density = Density.from_file(path.as_posix())
    density.add_bounds()
    return density


@contextlib.contextmanager
def use[T](var: T):
    try:
        yield var
    finally:
        del var


@contextlib.contextmanager
def computations():
    cmps: dict[str, dict | float] = {}
    try:
        yield cmps
    finally:
        for k, v in times(cmps):
            log_step(k.removesuffix(' time'), v)
