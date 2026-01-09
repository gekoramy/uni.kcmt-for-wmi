import argparse
import dataclasses
import itertools as it
import typing as t
from datetime import timedelta
from pathlib import Path

import math
import numpy as np
import polars as pl
from matplotlib import pyplot as plt, transforms, ticker, collections

from src import utils


@dataclasses.dataclass(frozen=True)
class Timeout:
    enumerator: timedelta
    compilator: timedelta
    tlemmas: timedelta


enumerator2steps: dict[str, list[str]] = {
    'sae': [
        'sae'
    ],
    **{
        f'decdnnf_baseline_{compiler}': [
            'tlemmas',
            f'tddnnf_{compiler}',
            f'decdnnf_{compiler}',
            f'decdnnf_baseline_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'decdnnf_two_steps_exists_{qo}_{compiler}': [
            'tlemmas',
            f'tddnnf_{compiler}',
            f'tddnnf_exists_{qo}_{compiler}',
            f'decdnnf_exists_{qo}_{compiler}',
            f'decdnnf_two_steps_exists_{qo}_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
        for qo in 'xA'
    },
}


def from_step(timeout: Timeout, step: str):
    if 'tlemmas' in step:
        return timeout.tlemmas

    if 'tddnnf' in step:
        return timeout.compilator

    if 'decdnnf' in step or 'sae' in step:
        return timeout.enumerator

    raise RuntimeError(f'unable to infer timeout from step name: {step}')


def label(step: str) -> str:
    return step.replace('_', ' ')


def plot(
        df: pl.DataFrame,
        column: str,
) -> plt.Figure:
    padding: float = 2

    minimum: float = (
            df.select(
                pl.col(f'{column}_{enum}')
                for enum in enumerator2steps.keys()
            )
            .min_horizontal()
            .min()
            / padding
    )

    maximum: float = (
        df.select(
            pl.col(f'{column}_{enum}')
            for enum in enumerator2steps.keys()
        )
        .max_horizontal()
        .max()
    )

    tot: int = math.comb(len(enumerator2steps), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for ((enum_x, steps_x), (enum_y, steps_y)), ax in zip(
            it.combinations(enumerator2steps.items(), 2),
            iter4axs,
    ):
        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='bottom',
            )

        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                pl.col(f'{column}_{enum_x}'),
                pl.col(f'{column}_{enum_y}'),
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x + steps_y)
                ],
            )
        )

        rm = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(f'{column}_{enum_x}').to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            xs[mask] = limit

        ys = data.get_column(f'{column}_{enum_y}').to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            ys[mask] = limit

        ax.scatter(
            x=xs[~rm],
            y=ys[~rm],
            color='C0',
            alpha=.5,
        )

        ax.scatter(
            x=xs[rm],
            y=ys[rm],
            color='C0',
            alpha=.5,
            marker='x'
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle(column)
    fig.tight_layout()
    return fig


def plot_time(
        df: pl.DataFrame,
        timeout: Timeout,
) -> plt.Figure:
    padding: float = 2
    minimum: float = (
            df.select(
                pl.col(f's_{enum}')
                for enum in enumerator2steps.keys()
            )
            .min_horizontal()
            .min()
            / padding
    )

    tot: int = math.comb(len(enumerator2steps), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for ((enum_x, steps_x), (enum_y, steps_y)), ax in zip(
            it.combinations(enumerator2steps.items(), 2),
            iter4axs,
    ):

        limits_x: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_x]))
        limits_x.append(padding * limits_x[-1])
        limits_y: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_y]))
        limits_y.append(padding * limits_y[-1])

        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='bottom',
            )

        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                *[
                    pl.col(f's_{step}')
                    for step in set(steps_x + steps_y)
                ],
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x + steps_y)
                ],
            ).with_columns(**{
                enum_x: pl.sum_horizontal(pl.col(f's_{step}') for step in steps_x),
                enum_y: pl.sum_horizontal(pl.col(f's_{step}') for step in steps_y),
            })
        )

        rm = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(enum_x).to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            xs[mask] = limit

        ys = data.get_column(enum_y).to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            ys[mask] = limit

        ax.scatter(
            x=xs[~rm],
            y=ys[~rm],
            color='C0',
            alpha=.5,
        )

        ax.scatter(
            x=xs[rm],
            y=ys[rm],
            color='C0',
            alpha=.5,
            marker='x'
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle('time')
    fig.tight_layout()
    return fig


def models_to_npolys(
        df: pl.DataFrame,
) -> plt.Figure:
    padding: float = 2

    subset: dict[str, list[str]] = {
        enum: steps
        for enum, steps in enumerator2steps.items()
        if 'exists' in enum
    }

    columns: list[tuple[str, str]] = [
        (
            f'models_{steps[-2]}',
            f'npolys_{steps[-1]}',
        )
        for steps in subset.values()
    ]

    minimum: float = (
            df.select(set(it.chain(*columns)))
            .min_horizontal()
            .min() / padding
    )

    maximum: float = (
        df.select(set(it.chain(*columns)))
        .max_horizontal()
        .max()
    )

    tot: int = math.comb(len(subset), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for (((enum_x, steps_x), cols_x), ((enum_y, steps_y), cols_y)), ax in zip(
            it.combinations(zip(subset.items(), columns), 2),
            iter4axs,
    ):
        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='darkgrey', linestyle='--')
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='bottom',
            )

        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                *(
                    pl.col(col)
                    for col in set(cols_x + cols_y)
                ),
                **{
                    f'tout_{step}': pl.col(f'stderr_{step}').fill_null('').str.contains('timeout')
                    for step in set(steps_x + steps_y)
                },
            )
        )

        src_rm = np.zeros(len(df), dtype=np.bool)
        trg_rm = np.zeros(len(df), dtype=np.bool)

        src_x = data.get_column(f'{cols_x[0]}').to_numpy(writable=True)
        trg_x = data.get_column(f'{cols_x[1]}').to_numpy(writable=True)
        for i, step, limit in zip(it.count(), steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            if i <= len(steps_x) - 2:
                src_rm |= mask
                src_x[mask] = limit
            trg_x[mask] = limit
            trg_rm |= mask

        src_y = data.get_column(f'{cols_y[0]}').to_numpy(writable=True)
        trg_y = data.get_column(f'{cols_y[1]}').to_numpy(writable=True)
        for i, step, limit in zip(it.count(), steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            if i <= len(steps_y) - 2:
                src_rm |= mask
                src_y[mask] = limit
            trg_y[mask] = limit
            trg_rm |= mask

        src: np.ndarray[tuple[int, t.Literal[2]], np.dtype[np.int64]] = np.column_stack((src_x, src_y))
        trg: np.ndarray[tuple[int, t.Literal[2]], np.dtype[np.int64]] = np.column_stack((trg_x, trg_y))

        lines = collections.LineCollection(
            segments=(np.stack((src, trg), axis=1)),
            alpha=0.5,
        )

        ax.add_collection(
            lines
        )

        ax.scatter(
            x=src_x[src_rm],
            y=src_y[src_rm],
            color='C0',
            alpha=.5,
            marker='x'
        )

        ax.scatter(
            x=trg_x[trg_rm],
            y=trg_y[trg_rm],
            color='C0',
            alpha=.5,
            marker='x'
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle('models → npolys')
    fig.tight_layout()
    return fig


def survival(
        df: pl.DataFrame,
) -> plt.Figure:
    tot: int = len(enumerator2steps)
    nrows: int = 1
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(
        nrows,
        ncols,
        width_ratios=[1 + len(steps) for steps in enumerator2steps.values()],
        figsize=(8 * ncols, 8 * nrows),
        sharey=True,
    )

    ax: plt.Axes
    for ax, (enumerator, steps) in zip(axs, enumerator2steps.items()):

        ax.grid(True, 'major', axis='x')
        ax.grid(True, 'both', axis='y')
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.set_axisbelow(True)
        ax.tick_params(
            axis='x',
            which='major',
            bottom=False,
            top=False,
            labelbottom=False,
        )

        cols: list[str] = [f'stderr_{step}' for step in steps]

        timeouts: pl.DataFrame = df.select(
            pl.col(step)
            .filter(pl.col(step).cast(pl.Utf8).str.contains('timeout'))
            .count()
            .alias(step)
            for step in cols
        )

        timed_out: list[int] = [
            timeouts[step].first()
            for step in cols
        ]

        xs = np.arange(1 + len(steps), dtype=np.int64)
        ys = list(it.accumulate(timed_out, lambda acc, x: acc - x, initial=len(df)))
        ax.plot(xs, ys, 'o--')
        ax.fill_between(xs, 0, ys, alpha=.5)

        ax.set_xlim(xs[0] - .5, xs[-1] + .5)
        ax.set_ylim(0, len(df) + 1)

        for x, step in zip(xs[1:], steps):
            ax.text(
                x=x,
                y=0,
                s=label(step),
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=-10, y=+10),
                va='bottom',
            )

    fig.suptitle('survival')
    fig.tight_layout()
    return fig


def foreach_step(
        df: pl.DataFrame,
        column: str,
) -> plt.Figure:
    tot: int = len(enumerator2steps)
    nrows: int = 2
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(
        nrows,
        ncols,
        figsize=(8 * ncols, 16 * nrows),
        sharey=True,
        sharex=True,
    )

    iter4axs: t.Iterable[plt.Axes] = iter(it.chain(*axs))
    ax: plt.Axes
    height: float = 1 / (1 + max(map(len, enumerator2steps.values())))

    for ax, (enumerator, steps) in zip(iter4axs, enumerator2steps.items()):
        ax.invert_yaxis()
        ax.grid(True, 'both', axis='x')
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.set_axisbelow(True)
        ax.tick_params(
            axis='x',
            which='both',
            bottom=True,
            top=True,
            labelbottom=True,
            labeltop=True,
        )

        data: pl.DataFrame = df.select(
            *[
                pl.col(f'{column}_{step}')
                for step in steps
            ],
            *[
                pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                for step in steps
            ],
        )

        ys: np.ndarray[tuple[int], np.dtype[np.int32]] = np.arange(len(data), dtype=np.int32) + 1
        for i, step in enumerate(steps):
            offset = height * i

            mask: np.ndarray[tuple[int], np.dtype[np.bool]] = data.get_column(f'tout_{step}').to_numpy()
            xs: np.ndarray[tuple[int], np.dtype[np.float64]] = data.get_column(f'{column}_{step}').to_numpy()

            ax.hlines(y=ys[~mask] + offset, xmin=0, xmax=xs[~mask], colors=f'C{i}', linestyles='-', label=label(step))
            ax.hlines(y=ys[mask] + offset, xmin=0, xmax=xs[mask], colors=f'C{i}', linestyles='--')

            ax.scatter(y=ys[~mask] + offset, x=xs[~mask], marker='|', c=f'C{i}')
            ax.scatter(y=ys[mask] + offset, x=xs[mask], marker='x', c=f'C{i}')

        ax.legend(loc='upper right', ncols=1)
        ax.set_xscale('log')

    fig.suptitle(column)
    fig.tight_layout()
    return fig


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=utils.file, required=True)
    parser.add_argument('--column', type=str, required=True)
    parser.add_argument('--output', type=Path, required=True, nargs='+')
    parser.add_argument('--timeout_enumerator', type=int, required=True)
    parser.add_argument('--timeout_compilator', type=int, required=True)
    parser.add_argument('--timeout_tlemmas', type=int, required=True)
    parser.add_argument('--type', type=str, required=False)
    args: argparse.Namespace = parser.parse_args()

    df: pl.DataFrame = pl.read_csv(
        args.csv,
        has_header=True,
    ).with_columns(
        **{
            f'stderr_{step}': pl.coalesce(pl.col(f'^stderr_{step}$'), pl.lit(None))
            for steps in enumerator2steps.values()
            for step in steps
        },
    ).sort(by=pl.col('density'))

    fig: plt.Figure
    match args.type:
        case 'steps':
            fig = foreach_step(df, args.column)

        case _:
            match args.column:
                case 'time':
                    fig = plot_time(df, Timeout(
                        enumerator=timedelta(minutes=args.timeout_enumerator),
                        compilator=timedelta(minutes=args.timeout_compilator),
                        tlemmas=timedelta(minutes=args.timeout_tlemmas),
                    ))

                case 'models to npolys':
                    fig = models_to_npolys(df)

                case 'survival':
                    fig = survival(df)

                case column:
                    fig = plot(df, column)

    for out in args.output:
        fig.savefig(out)


if __name__ == '__main__':
    main()
