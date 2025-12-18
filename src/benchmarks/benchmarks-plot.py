import itertools as it
from pathlib import Path

import math
import polars as pl
from matplotlib import pyplot as plt


def plot(df: pl.DataFrame, enumerators: list[str], column: str) -> plt.Figure:

    padding: float = 21 / 20

    maximum: float = (
        df.select(
            pl.col(f'{column}_{enum}')
            for enum in enumerators
        )
        .max()
        .max_horizontal()
        .first()
    )

    limit: float = maximum * padding

    fig, axs = plt.subplots(1, math.comb(len(enumerators), 2), figsize=(6 * 3, 6 * 1), )

    ax: plt.Axes
    for (enum_x, enum_y), ax in zip(it.combinations(enumerators, 2), axs):
        both: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_not_null() & pl.col(f'{column}_{enum_y}').is_not_null()
            )
        )

        tout: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_null() | pl.col(f'{column}_{enum_y}').is_null()
            )
        )

        ax.set_xlim(0, limit * padding)
        ax.set_ylim(0, limit * padding)

        ax.axvline(x=limit, color='darkgrey', linestyle='--')
        ax.axhline(y=limit, color='darkgrey', linestyle='--')

        ax.axline((0, 0), slope=1, color='darkgrey', linestyle=':')

        for x in ax.get_xticks()[1:]:
            ax.axline((0, x), slope=1, color='darkgrey', linestyle=':', linewidth=.75, alpha=.5)

        for y in ax.get_yticks()[1:]:
            ax.axline((y, 0), slope=1, color='darkgrey', linestyle=':', linewidth=.75, alpha=.5)

        ax.scatter(
            x=both.select_seq(pl.col(f'{column}_{enum_x}')),
            y=both.select_seq(pl.col(f'{column}_{enum_y}')),
            color='C0',
            alpha=.5,
        )

        ax.scatter(
            x=tout.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit)),
            y=tout.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit)),
            marker='x',
            color='C1',
            alpha=.5,
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle(column)
    return fig


if __name__ == '__main__':

    rsc: Path = Path(__file__).parent.parent.parent / 'resources'
    enumerators: list[str] = ['sae', 'd4', 'sdd']

    df: pl.DataFrame = pl.read_csv(
        rsc / 'merge.csv',
        has_header=True,
    ).with_columns(
        pl.col('enumerating_sae').alias('enumerating full_sae'),
        *[
            (
                pl.col(f'enumerating_{tdd}')
                .sub(pl.col(f'lemmas loading_{tdd}'))
                .add(pl.col('Partial AllSMT'))
                .add(pl.col('extract tlemmas'))
            ).alias(f'enumerating full_{tdd}')
            for tdd in ['d4', 'sdd']
        ],
    )

    for column in ['enumerating', 'npolys', 'enumerating full']:
        fig: plt.Figure = plot(df, enumerators, column)
        fig.savefig(rsc / f'{column}.pdf')
