"""
xvec_plotting_scaled.py

Optimized plotting utilities for Xvec zonal-statistics outputs.

Features
--------
- Uses Xvec (`DataArray.xvec.plot`) for spatial maps.
- Supports Dataset or DataArray inputs.
- Supports `time` or `cdr_period` temporal dimensions.
- Supports Xvec `zonal_statistics` outputs.
- Filters by city, zone category, or zone ID.
- Supports raw, z-score, and min-max scaling.
- Supports robust and symmetric color scaling for maps.
- Works with a custom colormap such as `metref_cmap`.
- Returns figures/axes so you can further edit or save them.
"""

from __future__ import annotations

import math
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, TwoSlopeNorm


# =====================================================================
# Helpers
# =====================================================================

def _as_list(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, np.integer, np.floating)):
        return [value]
    return list(value)


def _get_dataarray(data, variable=None):
    if isinstance(data, xr.Dataset):
        if variable is None:
            if len(data.data_vars) == 1:
                variable = next(iter(data.data_vars))
            else:
                raise ValueError(
                    "Provide `variable=` when Dataset contains multiple variables. "
                    f"Available: {list(data.data_vars)}"
                )
        if variable not in data.data_vars:
            raise KeyError(
                f"Variable {variable!r} not found. Available: {list(data.data_vars)}"
            )
        return data[variable], variable

    if isinstance(data, xr.DataArray):
        return data, variable or data.name or "value"

    raise TypeError("`data` must be an xarray Dataset or DataArray.")


def _infer_time_dim(data, time_dim=None):
    if time_dim is not None:
        if time_dim not in data.dims:
            raise KeyError(
                f"Time dimension {time_dim!r} not found. "
                f"Available dimensions: {list(data.dims)}"
            )
        return time_dim

    for candidate in ("cdr_period", "time", "date", "period"):
        if candidate in data.dims:
            return candidate
    return None


def _select_statistic(data, statistic="mean", statistic_dim="zonal_statistics"):
    if statistic_dim not in data.dims:
        return data

    available = [str(v) for v in data[statistic_dim].values]

    if statistic is None:
        if "mean" in available:
            statistic = "mean"
        elif len(available) == 1:
            statistic = available[0]
        else:
            raise ValueError(
                "`statistic=` is required because multiple zonal statistics are present: "
                f"{available}"
            )

    if statistic not in available:
        raise KeyError(
            f"Statistic {statistic!r} not found. Available: {available}"
        )

    return data.sel({statistic_dim: statistic}, drop=True)


def _compute_scalar(value):
    if hasattr(value, "compute"):
        value = value.compute()
    return float(value)


def _safe_std(data, dim):
    std = data.std(dim=dim, skipna=True)
    return std.where(std > 0)


# =====================================================================
# Scaling
# =====================================================================

def scale_data(data, *, method=None, dim=None):
    """
    Scale an xarray DataArray.

    Parameters
    ----------
    method : {None, "zscore", "minmax"}
        None      -> raw values
        zscore    -> (x - mean) / std
        minmax    -> (x - min) / (max - min)
    dim : str or sequence[str]
        Dimension(s) over which scaling statistics are calculated.
    """
    if method is None:
        return data

    method = str(method).lower()
    if dim is None:
        raise ValueError("`dim=` must be provided when scaling is requested.")

    if method == "zscore":
        mean = data.mean(dim=dim, skipna=True)
        std = _safe_std(data, dim=dim)
        return (data - mean) / std

    if method == "minmax":
        minimum = data.min(dim=dim, skipna=True)
        maximum = data.max(dim=dim, skipna=True)
        span = (maximum - minimum).where((maximum - minimum) > 0)
        return (data - minimum) / span

    raise ValueError("`method` must be None, 'zscore', or 'minmax'.")


def _scale_label(variable, statistic, scale):
    if scale == "zscore":
        return f"{variable} · standardized z-score"
    if scale == "minmax":
        return f"{variable} · scaled 0–1"
    return f"{variable} · zonal {statistic}"


# =====================================================================
# Selection
# =====================================================================

def select_vector_zones(
    data,
    *,
    cities=None,
    zone_categories=None,
    zone_ids=None,
    zone_dim="zone",
    city_coord="city_name",
    category_coord="zone_cat",
    id_coord="norm_id",
):
    """Positionally filter an Xvec vector cube."""
    if zone_dim not in data.dims:
        raise KeyError(
            f"Dimension {zone_dim!r} not found. Available dimensions: {list(data.dims)}"
        )

    mask = np.ones(data.sizes[zone_dim], dtype=bool)
    filters = {
        city_coord: _as_list(cities),
        category_coord: _as_list(zone_categories),
        id_coord: _as_list(zone_ids),
    }

    for coordinate, selected_values in filters.items():
        if selected_values is None:
            continue
        if coordinate not in data.coords:
            raise KeyError(
                f"Coordinate {coordinate!r} not found. Available coordinates: {list(data.coords)}"
            )

        coordinate_values = np.asarray(data[coordinate].values)
        if coordinate_values.dtype.kind in {"O", "U", "S"}:
            coordinate_values = np.char.lower(coordinate_values.astype(str))
            selected_values = [str(v).lower() for v in selected_values]

        mask &= np.isin(coordinate_values, selected_values)

    positions = np.flatnonzero(mask)
    if positions.size == 0:
        raise ValueError("No zones matched the requested filters.")

    return data.isel({zone_dim: positions})


def select_plot_data(
    data,
    variable=None,
    *,
    statistic="mean",
    statistic_dim="zonal_statistics",
    cities=None,
    zone_categories=None,
    zone_ids=None,
    zone_dim="zone",
    city_coord="city_name",
    category_coord="zone_cat",
    id_coord="norm_id",
    time_dim=None,
    periods=None,
    time_range=None,
    time_index=None,
):
    da, variable = _get_dataarray(data, variable)
    da = _select_statistic(da, statistic=statistic, statistic_dim=statistic_dim)

    if zone_dim in da.dims and any(v is not None for v in (cities, zone_categories, zone_ids)):
        da = select_vector_zones(
            da,
            cities=cities,
            zone_categories=zone_categories,
            zone_ids=zone_ids,
            zone_dim=zone_dim,
            city_coord=city_coord,
            category_coord=category_coord,
            id_coord=id_coord,
        )

    resolved_time = _infer_time_dim(da, time_dim)

    if resolved_time is not None:
        if periods is not None:
            da = da.sel({resolved_time: periods})
        elif time_range is not None:
            if len(time_range) != 2:
                raise ValueError("`time_range` must be (start, end).")
            da = da.sel({resolved_time: slice(time_range[0], time_range[1])})
        elif time_index is not None:
            da = da.isel({resolved_time: time_index})

        if da.sizes[resolved_time] == 0:
            raise ValueError("No timestamps remain after time selection.")

    return da, variable, resolved_time


# =====================================================================
# Color limits
# =====================================================================

def _data_limits(data, *, vmin=None, vmax=None, robust=False, symmetric=False):
    if robust and (vmin is None or vmax is None):
        q = data.quantile([0.02, 0.98], skipna=True)
        if hasattr(q, "compute"):
            q = q.compute()
        if vmin is None:
            vmin = float(q.sel(quantile=0.02))
        if vmax is None:
            vmax = float(q.sel(quantile=0.98))

    if vmin is None:
        vmin = _compute_scalar(data.min(skipna=True))
    if vmax is None:
        vmax = _compute_scalar(data.max(skipna=True))

    if not np.isfinite(vmin) or not np.isfinite(vmax):
        raise ValueError("Selected data contain no finite values.")

    if symmetric:
        limit = max(abs(vmin), abs(vmax))
        if np.isclose(limit, 0):
            limit = 1e-9
        vmin, vmax = -limit, limit
    elif np.isclose(vmin, vmax):
        vmax = vmin + 1e-9

    return vmin, vmax


# =====================================================================
# Xvec maps
# =====================================================================

def plot_zonal_maps(
    data,
    variable=None,
    *,
    statistic="mean",
    statistic_dim="zonal_statistics",
    cities=None,
    zone_categories=None,
    zone_ids=None,
    zone_dim="zone",
    city_coord="city_name",
    category_coord="zone_cat",
    id_coord="norm_id",
    time_dim=None,
    periods=None,
    time_range=None,
    time_index=None,
    col_wrap=4,
    cmap="viridis",
    scale=None,
    scale_dim=None,
    vmin=None,
    vmax=None,
    robust=False,
    symmetric=False,
    center=0.0,
    figsize=None,
    title=None,
    colorbar_label=None,
    edgecolor="black",
    linewidth=0.20,
    wspace=0.01,
    hspace=0.04,
    panel_width=4.0,
    panel_height=3.2,
):
    """
    Plot zonal statistics as Xvec spatial facets.

    scale=None      -> raw physical units
    scale='zscore'  -> standardize along scale_dim (defaults to time)
    scale='minmax'  -> scale to 0–1 along scale_dim (defaults to time)
    """
    plot_data, variable, resolved_time = select_plot_data(
        data,
        variable,
        statistic=statistic,
        statistic_dim=statistic_dim,
        cities=cities,
        zone_categories=zone_categories,
        zone_ids=zone_ids,
        zone_dim=zone_dim,
        city_coord=city_coord,
        category_coord=category_coord,
        id_coord=id_coord,
        time_dim=time_dim,
        periods=periods,
        time_range=time_range,
        time_index=time_index,
    )

    if scale is not None:
        if scale_dim is None:
            if resolved_time is None:
                raise ValueError("Map scaling needs `scale_dim=` when no temporal dimension exists.")
            scale_dim = resolved_time

        plot_data = scale_data(plot_data, method=scale, dim=scale_dim)

        if scale == "minmax":
            vmin = 0.0 if vmin is None else vmin
            vmax = 1.0 if vmax is None else vmax
        elif scale == "zscore":
            symmetric = True

    vmin, vmax = _data_limits(
        plot_data,
        vmin=vmin,
        vmax=vmax,
        robust=robust,
        symmetric=symmetric,
    )

    n_panels = plot_data.sizes.get(resolved_time, 1) if resolved_time else 1
    ncols = min(col_wrap, n_panels)
    nrows = math.ceil(n_panels / ncols)

    if figsize is None:
        figsize = (panel_width * ncols, panel_height * nrows)

    plt.close("all")

    plot_kwargs = dict(
        cmap=cmap,
        legend=False,
        figsize=figsize,
        vmin=vmin,
        vmax=vmax,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )

    if resolved_time is not None:
        fig, axes = plot_data.xvec.plot(
            col=resolved_time,
            col_wrap=col_wrap,
            **plot_kwargs,
        )
    else:
        fig, axes = plot_data.xvec.plot(**plot_kwargs)

    map_axes = list(np.atleast_1d(axes).ravel())

    for extra_axis in list(fig.axes):
        if not any(extra_axis is axis for axis in map_axes):
            fig.delaxes(extra_axis)

    for i, ax in enumerate(map_axes):
        if i >= n_panels:
            ax.set_visible(False)
            continue

        ax.set_axis_off()
        ax.margins(0)
        ax.set_anchor("C")

        if resolved_time:
            old_title = ax.get_title()
            new_title = old_title.replace(f"{resolved_time} = ", "").replace("time = ", "")
            ax.set_title(new_title, fontsize=9, pad=2)

    fig.subplots_adjust(
        left=0.01,
        right=0.99,
        top=0.91,
        bottom=0.12,
        wspace=wspace,
        hspace=hspace,
    )

    if symmetric or (vmin < center < vmax):
        norm = TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)

    mappable = ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])

    cbar_ax = fig.add_axes([0.25, 0.045, 0.50, 0.018])
    colorbar = fig.colorbar(mappable, cax=cbar_ax, orientation="horizontal")
    colorbar.set_label(colorbar_label or _scale_label(variable, statistic, scale))

    fig.suptitle(
        title or _scale_label(variable, statistic, scale),
        fontsize=15,
        y=0.975,
    )

    return fig, axes, plot_data


def plot_metref_maps(
    data,
    variable="metref_mean",
    *,
    metref_cmap,
    statistic="mean",
    periods=None,
    time_range=None,
    time_index=None,
    scale=None,
    anomaly=None,
    **kwargs,
):
    """Convenience wrapper using your existing `metref_cmap`."""
    if anomaly is None:
        name = variable.lower()
        anomaly = ("anomaly" in name) or name.endswith("_z")

    return plot_zonal_maps(
        data,
        variable=variable,
        statistic=statistic,
        periods=periods,
        time_range=time_range,
        time_index=time_index,
        cmap=metref_cmap,
        scale=scale,
        symmetric=anomaly,
        center=0.0,
        **kwargs,
    )


# =====================================================================
# One variable across several zones
# =====================================================================

def plot_zone_timeseries(
    data,
    variable=None,
    *,
    statistic="mean",
    cities=None,
    zone_categories=None,
    zone_ids=None,
    zone_dim="zone",
    city_coord="city_name",
    category_coord="zone_cat",
    id_coord="norm_id",
    time_dim=None,
    start=None,
    end=None,
    aggregation="mean",
    rolling_window=None,
    scale=None,
    scale_scope="per_series",
    figsize=(14, 6),
    title=None,
    ylabel=None,
    marker=None,
    linewidth=1.8,
    grid=True,
):
    """
    Plot ONE variable through time for several zones/cities.

    scale_scope='per_series'
        Each zone scaled independently through time. Best for shape/timing.

    scale_scope='global'
        One scale computed across selected zones + time. Better when you want
        standardized values but still preserve relative between-zone levels.
    """
    source, variable, resolved_time = select_plot_data(
        data,
        variable,
        statistic=statistic,
        cities=cities,
        zone_categories=zone_categories,
        zone_ids=zone_ids,
        zone_dim=zone_dim,
        city_coord=city_coord,
        category_coord=category_coord,
        id_coord=id_coord,
        time_dim=time_dim,
    )

    if resolved_time is None:
        raise KeyError("Selected variable has no temporal dimension.")

    if start is not None or end is not None:
        source = source.sel({resolved_time: slice(start, end)})

    if source.sizes[resolved_time] == 0:
        raise ValueError("No timestamps remain after date filtering.")

    if scale_scope not in {"per_series", "global"}:
        raise ValueError("`scale_scope` must be 'per_series' or 'global'.")

    if scale is not None and scale_scope == "global":
        source = scale_data(
            source,
            method=scale,
            dim=[resolved_time, zone_dim],
        )

    if cities is not None and city_coord in source.coords:
        labels = np.asarray(source[city_coord].values).astype(str)
    elif id_coord in source.coords:
        labels = np.asarray(source[id_coord].values).astype(str)
    else:
        labels = np.asarray(source[zone_dim].values).astype(str)

    label_order = list(dict.fromkeys(labels))
    fig, ax = plt.subplots(figsize=figsize)

    for label in label_order:
        positions = np.flatnonzero(labels == label)
        series = source.isel({zone_dim: positions})

        if series.sizes[zone_dim] > 1:
            if aggregation == "mean":
                series = series.mean(zone_dim, skipna=True)
            elif aggregation == "median":
                series = series.median(zone_dim, skipna=True)
            elif aggregation == "sum":
                series = series.sum(zone_dim, skipna=True)
            else:
                raise ValueError("`aggregation` must be 'mean', 'median', or 'sum'.")
        else:
            series = series.isel({zone_dim: 0}, drop=True)

        if scale is not None and scale_scope == "per_series":
            series = scale_data(series, method=scale, dim=resolved_time)

        if rolling_window is not None:
            series = series.rolling(
                {resolved_time: rolling_window},
                center=True,
                min_periods=1,
            ).mean()

        ax.plot(
            series[resolved_time].values,
            series.values,
            label=label,
            linewidth=linewidth,
            marker=marker,
        )

    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel or _scale_label(variable, statistic, scale))
    ax.set_title(title or f"{variable} through time by zone")

    if len(label_order) <= 15:
        ax.legend(
            title="Zone",
            frameon=False,
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
        )

    if grid:
        ax.grid(alpha=0.3, linestyle="--")

    if scale == "zscore":
        ax.axhline(0, linewidth=1, alpha=0.5)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig, ax, source


# =====================================================================
# Several variables for one zone
# =====================================================================

def plot_zone_variables(
    data,
    zone,
    variables,
    *,
    statistic="mean",
    zone_coord="city_name",
    zone_dim="zone",
    time_dim=None,
    start=None,
    end=None,
    aggregation="mean",
    scale=None,
    rolling_window=None,
    figsize=(14, 6),
    title=None,
    ylabel=None,
    grid=True,
):
    """
    Plot SEVERAL variables through time for ONE zone/city.

    scale=None      -> raw units
    scale='zscore'  -> recommended when variables have different units
    scale='minmax'  -> 0-1 comparison, useful for dashboards

    Each variable is scaled independently through time.
    """
    if not isinstance(data, xr.Dataset):
        raise TypeError("`data` must be an xr.Dataset.")

    if zone_coord not in data.coords:
        raise KeyError(
            f"Coordinate {zone_coord!r} not found. Available: {list(data.coords)}"
        )

    values = np.asarray(data[zone_coord].values).astype(str)
    positions = np.flatnonzero(
        np.char.lower(values) == str(zone).lower()
    )

    if positions.size == 0:
        raise ValueError(f"No zone matched {zone!r}.")

    selected = data.isel({zone_dim: positions})
    fig, ax = plt.subplots(figsize=figsize)

    for variable in variables:
        da, resolved_name = _get_dataarray(selected, variable)
        da = _select_statistic(da, statistic=statistic)
        resolved_time = _infer_time_dim(da, time_dim)

        if resolved_time is None:
            raise KeyError(f"{variable!r} has no temporal dimension.")

        if start is not None or end is not None:
            da = da.sel({resolved_time: slice(start, end)})

        if da.sizes[zone_dim] > 1:
            if aggregation == "mean":
                da = da.mean(zone_dim, skipna=True)
            elif aggregation == "median":
                da = da.median(zone_dim, skipna=True)
            elif aggregation == "sum":
                da = da.sum(zone_dim, skipna=True)
            else:
                raise ValueError("`aggregation` must be 'mean', 'median', or 'sum'.")
        else:
            da = da.isel({zone_dim: 0}, drop=True)

        if scale is not None:
            da = scale_data(da, method=scale, dim=resolved_time)

        if rolling_window is not None:
            da = da.rolling(
                {resolved_time: rolling_window},
                center=True,
                min_periods=1,
            ).mean()

        ax.plot(
            da[resolved_time].values,
            da.values,
            label=resolved_name,
            linewidth=1.8,
        )

    ax.set_xlabel("Date")

    if ylabel is None:
        if scale == "zscore":
            ylabel = "Standardized value (z-score)"
        elif scale == "minmax":
            ylabel = "Scaled value (0–1)"
        else:
            ylabel = f"Zonal {statistic}"

    ax.set_ylabel(ylabel)
    ax.set_title(title or f"Climate variables for {zone}")
    ax.legend(frameon=False)

    if grid:
        ax.grid(alpha=0.3, linestyle="--")

    if scale == "zscore":
        ax.axhline(0, linewidth=1, alpha=0.5)

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig, ax, selected


# Backward-compatible aliases
plot_city_timeseries = plot_zone_timeseries
plot_city_variables = plot_zone_variables
