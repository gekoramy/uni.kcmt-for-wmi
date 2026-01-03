import argparse
from datetime import timedelta
from pathlib import Path

from pysdd.sdd import Vtree, SddManager, SddNode


def minimize(vtree: tuple[Path, Path], sdd: tuple[Path, Path], timeout: timedelta):
    vt: Vtree = Vtree.from_file(str.encode(vtree[0].as_posix()))
    mgr: SddManager = SddManager.from_vtree(vt)
    phi: SddNode = mgr.read_sdd_file(str.encode(sdd[0].as_posix()))

    # from http://reasoning.cs.ucla.edu/sdd/doc/sdd-advanced-manual.pdf
    limits: list[int] = [180, 60, 30, 10]
    factor: float = max(1., timeout.total_seconds() / sum(limits))

    mgr.set_vtree_search_time_limit(limits[0] * factor)
    mgr.set_vtree_fragment_time_limit(limits[1] * factor)
    mgr.set_vtree_operation_time_limit(limits[2] * factor)
    mgr.set_vtree_apply_time_limit(limits[3] * factor)

    # default 1 << 13
    mgr.set_vtree_cartesian_product_limit(1 << 32)

    phi.ref()
    mgr.minimize_limited()

    mgr.vtree().save(str.encode(vtree[1].as_posix()))
    phi.save(str.encode(sdd[1].as_posix()))


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--vtree', nargs=2, type=Path, required=True)
    parser.add_argument('--sdd', nargs=2, type=Path, required=True)
    parser.add_argument('--minutes', type=int, required=True)
    args: argparse.Namespace = parser.parse_args()

    minimize(args.vtree, args.sdd, timedelta(minutes=args.minutes))


if __name__ == '__main__':
    main()
