from multiprocessing import Pool
from pathlib import Path

import polars as pl


def read_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(path, has_header=True, glob=False)


def main(paths: list[Path], output: Path, cores: int) -> None:
    with Pool(cores) as p:
        dataframes: list[pl.DataFrame] = p.map(read_csv, paths)

    stacked: pl.DataFrame = pl.concat(dataframes, how='diagonal')

    stacked.write_csv(output.as_posix())


if __name__ == '__main__':
    main(
        paths=[Path(path) for path in snakemake.input],
        output=Path(snakemake.output[0]),
        cores=snakemake.threads,
    )
