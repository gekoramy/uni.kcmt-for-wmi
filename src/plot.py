import argparse
import dataclasses
import itertools as it
import re
import typing as t
from collections import OrderedDict
from datetime import timedelta
from pathlib import Path

import math
import numpy as np
import polars as pl
import pypalettes
from matplotlib import pyplot as plt, transforms, ticker, colors

from src import utils


@dataclasses.dataclass(frozen=True)
class Timeout:
    enumerator: timedelta
    compilator: timedelta
    tlemmas: timedelta


enumerator2steps: dict[str, list[str]] = OrderedDict(
    **{
        'sae': [
            'sae'
        ],
        'sae_with_tlemmas': [
            'tlemmas_phi',
            'sae_with_tlemmas'
        ]
    },
    **{
        f'wmi_decdnnf_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'decdnnf_{compiler}_t_reduced',
            f'wmi_decdnnf_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_exists_{qo}_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'tddnnf_exists_{qo}_{compiler}_t_reduced',
            f'decdnnf_1st_step_exists_{qo}_{compiler}_t_reduced',
            f'decdnnf_2nd_step_exists_{qo}_{compiler}_t_reduced',
            f'wmi_decdnnf_exists_{qo}_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
        for qo in 'xA'
    },
    **{
        f'wmi_decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_phi',
            f'tddnnf_{compiler}_tlemmas_phi',
            f'decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            'tlemmas_not_phi',
            f'tddnnf_{compiler}_t_extended',
            f'decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_mathsat_{compiler}': [
            f'tddnnf_{compiler}_phi',
            f'decdnnf_n_mathsat_{compiler}',
            f'wmi_decdnnf_n_mathsat_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
)


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


def compare_columns(
        df: pl.DataFrame,
        columns_n_enumerators: list[tuple[tuple[str, str], str]],
) -> plt.Figure:
    minimum: float = (
        df.select(
            pl.col(column)
            for columns, _ in columns_n_enumerators
            for column in columns
        )
        .min_horizontal()
        .min()
    )
    minimum = 0.0 if minimum < 10 else minimum

    maximum: tuple[float, ...] = tuple(
        df.select(
            pl.col(columns[ix])
            for columns, _ in columns_n_enumerators
        )
        .max_horizontal()
        .max()
        for ix in range(2)
    )

    log_width: float = math.log10(max(1.0, maximum[0])) - math.log10(max(1.0, minimum))
    padding: float = 10 ** (max(1.0, log_width) / 10)

    tot: int = len(columns_n_enumerators)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    cmap = pypalettes.load_cmap('Sunset2')
    tmin, tmax = max(1.0, minimum), maximum[0] * padding
    major: np.ndarray[tuple[int], np.dtype[np.float64]] = ticker.LogLocator(base=10).tick_values(tmin, tmax)
    major = major[(tmin <= major) & (major <= tmax)]
    minor: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10, subs=np.arange(2, 12, 2)).tick_values(tmin, tmax)
    )
    minor = minor[(tmin <= minor) & (minor <= tmax)]

    ax: plt.Axes
    for ((col_x, col_y), enum), ax in zip(
            columns_n_enumerators,
            iter4axs,
    ):
        steps_x: list[str] = enumerator2steps[enum]
        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum[0] * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, maximum[1] * padding)
        ax.xaxis.set_major_locator(ticker.FixedLocator(major))
        ax.yaxis.set_major_locator(ticker.SymmetricalLogLocator(base=10, linthresh=1))
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.yaxis.set_minor_locator(ticker.SymmetricalLogLocator(base=10, subs=np.arange(2, 12, 2), linthresh=1))
        ax.grid(visible=True, which='both', linewidth=.1)

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        ax.plot(
            (minimum, max(limits_x)),
            (minimum, max(limits_x)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                pl.col(f'{col_x}'),
                pl.col(f'{col_y}'),
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x)
                ],
            )
        )

        rm = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(f'{col_x}').to_numpy(writable=True)
        ys = data.get_column(f'{col_y}').to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            xs[mask] = limit

        xy = np.column_stack((xs, ys))

        # count points at each location for non-timeout points
        unique_regular, counts_regular = np.unique(xy[~rm], axis=0, return_counts=True)

        # count points at each location for timeout points
        unique_timeout, counts_timeout = np.unique(xy[rm], axis=0, return_counts=True)

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                s=s * 80,
                zorder=3,
                **kwargs,
            )
            for xy, s, kwargs in [
                (unique_regular, counts_regular, dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (unique_timeout, counts_timeout, dict(marker='x', color=cmap(0))),
            ]
        ]

        ax.set_xlabel(label(col_x))
        ax.set_ylabel(label(col_y))
        ax.set_aspect('equal')

    fig.tight_layout()
    return fig


def plot(
        df: pl.DataFrame,
        title: str,
        columns_n_enumerators: list[tuple[str, str]] | None = None,
) -> plt.Figure:
    minimum: float = (
        df.select(
            pl.col(column)
            for column, _ in columns_n_enumerators
        )
        .min_horizontal()
        .min()
    )
    minimum = 0.0 if minimum < 10 else minimum

    maximum: float = (
        df.select(
            pl.col(column)
            for column, _ in columns_n_enumerators
        )
        .max_horizontal()
        .max()
    )

    log_width: float = math.log10(max(1.0, maximum)) - math.log10(max(1.0, minimum))
    padding: float = 10 ** (max(1.0, log_width) / 10)

    tot: int = math.comb(len(columns_n_enumerators), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    cmap = pypalettes.load_cmap('Sunset2')
    tmin, tmax = max(1.0, minimum), maximum * padding
    major: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10).tick_values(tmin, tmax)
    )
    major = major[(tmin <= major) & (major <= tmax)]
    minor: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10, subs=np.arange(2, 12, 2)).tick_values(tmin, tmax)
    )
    minor = minor[(tmin <= minor) & (minor <= tmax)]

    ax: plt.Axes
    for ((col_x, enum_x), (col_y, enum_y)), ax in zip(
            it.combinations(columns_n_enumerators, 2),
            iter4axs,
    ):
        steps_x: list[str] = enumerator2steps[enum_x]
        steps_y: list[str] = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])
        ax.xaxis.set_major_locator(ticker.FixedLocator(major))
        ax.yaxis.set_major_locator(ticker.FixedLocator(major))
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.yaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.grid(visible=True, which='both', linewidth=.1)

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
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
                pl.col(f'{col_x}'),
                pl.col(f'{col_y}'),
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x + steps_y)
                ],
            )
        )

        rm_x = np.zeros(len(df), dtype=np.bool)
        rm_y = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(f'{col_x}').to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_x |= mask
            xs[mask] = limit

        ys = data.get_column(f'{col_y}').to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_y |= mask
            ys[mask] = limit

        xy = np.column_stack((xs, ys))

        # count points at each location for non-timeout points
        unique_regular, counts_regular = np.unique(xy[~(rm_x | rm_y)], axis=0, return_counts=True)

        # count points at each location for timeout points
        unique_timeout_x, counts_timeout_x = np.unique(xy[rm_x & ~rm_y], axis=0, return_counts=True)
        unique_timeout_y, counts_timeout_y = np.unique(xy[~rm_x & rm_y], axis=0, return_counts=True)
        unique_timeout, counts_timeout = np.unique(xy[rm_x & rm_y], axis=0, return_counts=True)

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                s=s * 80,
                zorder=3,
                **kwargs,
            )
            for xy, s, kwargs in [
                (unique_regular, counts_regular, dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (unique_timeout_x, counts_timeout_x, dict(marker='3', color=cmap(0))),
                (unique_timeout_y, counts_timeout_y, dict(marker='1', color=cmap(0))),
                (unique_timeout, counts_timeout, dict(marker='x', color=cmap(0))),
            ]
        ]

        ax.set_xlabel(label(enum_x))
        ax.set_ylabel(label(enum_y))
        ax.set_aspect('equal')

    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_time(
        df: pl.DataFrame,
        timeout: Timeout,
        expression_n_enumerator: list[tuple[pl.Expr, str]],
) -> plt.Figure:
    padding: float = 1.4
    minimum: float = (
        df.select(
            expr.alias(enum)
            for expr, enum in expression_n_enumerator
        )
        .min_horizontal()
        .min()
    )
    minimum = 0 if minimum < padding else minimum / padding

    tot: int = math.comb(len(enumerator2steps), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    cmap = pypalettes.load_cmap('Sunset2')
    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for ((expression_x, enum_x), (expression_y, enum_y)), ax in zip(
            it.combinations(expression_n_enumerator, 2),
            iter4axs,
    ):
        steps_x = enumerator2steps[enum_x]
        steps_y = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_x]))
        limits_x.append(padding * limits_x[-1])
        limits_y: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_y]))
        limits_y.append(padding * limits_y[-1])

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(top=False, right=False)

        for i, (step, limit) in enumerate(zip(steps_x, limits_x)):
            height = limits_y[-1] * (padding ** i)
            ax.plot(
                [limit, limit], [minimum, height],
                color='black',
                linestyle='--',
                linewidth=1,
            )
            ax.text(
                x=limit,
                y=height,
                s=label(step),
                transform=transforms.offset_copy(ax.transData, units='dots', x=-4, y=-3),
                ha='right',
                va='top',
            )

        for i, (step, limit) in enumerate(zip(steps_y, limits_y)):
            width = limits_x[-1] * (padding ** i)
            ax.plot(
                [0, width], [limit, limit],
                color='black',
                linestyle='--',
                linewidth=1,
            )
            ax.text(
                x=width,
                y=limit,
                s=label(step),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=-3, y=-4),
                ha='right',
                va='bottom',
            )

        ax.set_xlim(minimum, limits_x[-1] * (padding ** (len(steps_y) - 1)))
        ax.set_ylim(minimum, limits_y[-1] * (padding ** (len(steps_x) - 1)))

        ax.grid(visible=True, which='both', linewidth=.1)
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
            ).with_columns(
                **{
                    enum_x: expression_x,
                    enum_y: expression_y,
                }
            )
        )

        rm_x = np.zeros(len(df), dtype=np.bool)
        xs = data.get_column(enum_x).to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_x |= mask
            xs[mask] = limit

        rm_y = np.zeros(len(df), dtype=np.bool)
        ys = data.get_column(enum_y).to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_y |= mask
            ys[mask] = limit

        coordinates = np.column_stack((xs, ys))

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                zorder=3,
                **kwargs,
            )
            for xy, kwargs in [
                (coordinates[~rm_x & ~rm_y], dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (coordinates[rm_x & ~rm_y], dict(marker='3', s=2 ** 6, color=cmap(0), alpha=.6)),
                (coordinates[~rm_x & rm_y], dict(marker='1', s=2 ** 6, color=cmap(0), alpha=.6)),
                (coordinates[rm_x & rm_y], dict(marker='x', color=cmap(0), alpha=.6)),
            ]
        ]

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle('time')
    fig.tight_layout()
    return fig


def plot_lines(
        df: pl.DataFrame,
        title: str,
        columns_n_enumerators: list[tuple[tuple[str, str], str]],
) -> plt.Figure:
    padding: float = 2

    columns: set[str] = {
        col
        for cols, _ in columns_n_enumerators
        for col in cols
    }

    minimum: float = (
        df.select(columns)
        .min_horizontal()
        .min()
    )
    minimum = 0 if minimum < padding else minimum / padding

    maximum: float = (
        df.select(columns)
        .max_horizontal()
        .max()
    )

    tot: int = math.comb(len(columns_n_enumerators), 2)
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(8 * ncols, 8 * nrows))

    iter4axs: t.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for ((cols_x, enum_x), (cols_y, enum_y)), ax in zip(
            it.combinations(columns_n_enumerators, 2),
            iter4axs,
    ):
        steps_x: list[str] = enumerator2steps[enum_x]
        steps_y: list[str] = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+5, y=+5),
                va='top',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
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

        ax.quiver(
            src_x,
            src_y,
            trg_x - src_x,
            trg_y - src_y,
            angles='xy',
            scale_units='xy',
            scale=1,
            alpha=0.5,
            color='C0',
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

    fig.suptitle(title)
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

    cmap = pypalettes.load_cmap('Sunset2')
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

        survived: pl.DataFrame = df.select(
            pl.col(f'stderr_{step}').cast(pl.Utf8).fill_null('').str.contains('timeout').alias(step)
            for step in steps
        ).select(
            pl.any_horizontal(steps[:i + 1]).not_().sum().alias(step)
            for i, step in enumerate(steps)
        )

        xs = np.arange(1 + len(steps), dtype=np.int64)
        ys = [len(df), *(survived[step].first() for step in steps)]
        ax.plot(xs, ys, 'o--', color=cmap(0))
        ax.fill_between(xs, 0, ys, color=cmap(0), alpha=.5)

        ax.set_xlim(xs[0] - .5, xs[-1] + .5)
        ax.set_ylim(0, len(df) + 1)

        for x, step in zip(xs[1:], steps):
            ax.text(
                x=x,
                y=0,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .8), ls=''),
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


def inspection(
        df: pl.DataFrame,
        qo: t.Literal['x', 'A'],
) -> plt.Figure:
    fig, ax = plt.subplots(1, 1, figsize=(300, 20))
    cmap: colors.Colormap = plt.get_cmap('tab20b')

    oq: t.Literal['x', 'A'] = 'xA'.replace(qo, '')

    enumerators: list[tuple[str, tuple[str, str, str]]] = [
        (enum, (f'models_{enum}', f'distinct_by_{oq}_{enum}', f'npolys_{enum}'))
        for enum in enumerator2steps.keys()
        if re.search(fr'sae|exists_{qo}', enum)
    ]

    many: int = sum(len(cols) for _, cols in enumerators)
    width: float = 1 / (many + len(enumerators) - 1)

    ax.set_axisbelow(True)
    ax.set_yscale('symlog', linthresh=10)
    ax.yaxis.set_minor_locator(ticker.FixedLocator([
        *range(0, 10, 2),
        *[
            x
            for exp in range(1, 6)
            for x in np.arange(2, 10) * (10 ** exp)
        ],
    ]))

    ax.grid()
    ax.yaxis.grid(which='minor')

    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.tick_params(
        axis='y',
        which='both',
        left=True,
        right=True,
        labelleft=True,
        labelright=True,
    )

    data: pl.DataFrame = df.select(
        *(
            col
            for _, cols in enumerators
            for col in cols
        )
    )

    xs: np.ndarray[tuple[int], np.dtype[np.int64]] = np.arange(len(data), dtype=np.int64) + 1
    for i, (enum, cols) in enumerate(enumerators):
        for j, col in enumerate(cols):
            offset: float = width * (4 * i + j)

            ax.bar(
                x=xs + offset,
                height=data.get_column(col).to_numpy(),
                color=cmap(4 * i + j),
                label=label(col),
                width=width,
            )

    ax.set_xlim(.5, len(data) + .5)
    ax.legend(loc='upper left', ncols=len(enumerators))

    fig.suptitle('inspection')
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

    timeout: Timeout = Timeout(
        enumerator=timedelta(minutes=args.timeout_enumerator),
        compilator=timedelta(minutes=args.timeout_compilator),
        tlemmas=timedelta(minutes=args.timeout_tlemmas),
    )

    fig: plt.Figure
    match args.type:
        case 'steps':
            fig = foreach_step(df, args.column)

        case 'only-decdnnf_n':
            match args.column:
                case 'models':
                    fig = plot(
                        df,
                        'models',
                        [
                            (f'{args.column}_{enum}', enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'decdnnf_n', enum)
                        ]
                    )

                case 'models to npolys':
                    fig = plot_lines(
                        df,
                        'models → npolys',
                        [
                            ((f'models_{enum}', f'npolys_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|decdnnf_n', enum)
                        ],
                    )

                case 'compare models vs npolys':
                    fig = compare_columns(
                        df,
                        [
                            ((f'npolys_{enum}', f'models_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|decdnnf_n', enum)
                        ],
                    )

        case 'only-exists':
            match args.column:
                case 'models to npolys':
                    fig = plot_lines(
                        df,
                        'models → npolys',
                        [
                            ((f'models_{enum}', f'npolys_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|exists', enum)
                        ],
                    )

                case 'models to nuniquepolys':
                    fig = plot_lines(
                        df,
                        'models → nuniquepolys',
                        [
                            ((f'models_{enum}', f'nuniquepolys_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|exists', enum)
                        ]
                    )

                case 'models to distinct_by_x' | 'models to distinct_by_A':
                    by: t.Literal['x', 'A'] = args.column[-1]
                    fig = plot_lines(
                        df,
                        f'models → distinct_by_{by}',
                        [
                            ((f'models_{enum}', f'distinct_by_{by}_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|exists', enum)
                        ],
                    )

                case 'models':
                    fig = plot(
                        df,
                        'models',
                        [
                            (f'{args.column}_{enum}', enum)
                            for enum in enumerator2steps.keys()
                            if re.search(r'sae|exists', enum)
                        ]
                    )

                case 'inspection-x':
                    fig = inspection(df, 'x')

                case 'inspection-A':
                    fig = inspection(df, 'A')

        case _:
            match args.column:
                case 'time':
                    fig = plot_time(
                        df,
                        timeout,
                        [
                            (pl.sum_horizontal(pl.col(f's_{step}') for step in steps), enum)
                            for enum, steps in enumerator2steps.items()
                        ]
                    )

                case 'enumerating':
                    fig = plot_time(
                        df,
                        timeout,
                        [
                            *[
                                (pl.sum_horizontal(pl.col(f's_{step}') for step in enumerator2steps[enum]), enum)
                                for enum in ['sae']
                            ],
                            *[
                                (pl.sum_horizontal(pl.col(f's_{step}') for step in steps if 'decdnnf' in step), enum)
                                for enum, steps in enumerator2steps.items()
                                if 'decdnnf' in enum
                            ],
                        ]
                    )

                case 'nuniquepolys to npolys':
                    fig = plot_lines(
                        df,
                        'nuniquepolys → npolys',
                        [
                            ((f'nuniquepolys_{enum}', f'npolys_{enum}'), enum)
                            for enum in enumerator2steps.keys()
                        ],
                    )

                case 'survival':
                    fig = survival(df)

                case 'distinct_by_x' | 'distinct_by_A':
                    by: t.Literal['x', 'A'] = args.column[-1]
                    fig = plot(
                        df,
                        'distinct_by',
                        [
                            (f'distinct_by_{by}_{enum}', enum)
                            for enum, _ in enumerator2steps.items()
                        ]
                    )

                case column:
                    fig = plot(
                        df,
                        column,
                        [
                            (f'{column}_{enum}', enum)
                            for enum, steps in enumerator2steps.items()
                        ],
                    )

    for out in args.output:
        fig.savefig(out)


if __name__ == '__main__':
    main()
