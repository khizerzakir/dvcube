`metref_mean` = each raster pixel's mean METREF during that half-month.  
`zonal stdev` = how variable those pixel-level half-month means are **within each polygon**.
It shows **spatial heterogeneity inside each mobility zone** for each half-month.


## 1. Basic usage

Import the functions:

```python
from plot_zonal_maps import (
    plot_metref_maps,
    plot_zonal_maps,
    plot_zone_timeseries,
    plot_zone_variables,
)
```

Ref-define or use the same metref_cmap

```python
fig, axes, selected = plot_metref_maps(
    stats,
    variable="metref_mean",
    statistic="mean",
    metref_cmap=metref_cmap,
    periods=[
        "2010-01-01",
        "2010-01-16",
        "2010-02-01",
        "2010-02-16",
    ],
    col_wrap=4,
)

plt.show()
```

The spatial maps are still drawn through Xvec itself using `xvec.plot()`.

---

## 2. What does each zonal statistic mean?

Assuming input variable is:

```python
variable="metref_mean"
```

Then:

| `statistic=` | Meaning on the map | Interpretation |
|---|---|---|
| `"mean"` | Average `metref_mean` of pixels inside the polygon | Typical METREF for the zone |
| `"min"` | Lowest pixel value inside the polygon | Lowest evaporative demand occurring somewhere in the zone |
| `"max"` | Highest pixel value inside the polygon | Highest evaporative demand occurring somewhere in the zone |
| `"median"` | Median pixel value | Robust central value, less affected by extremes |
| `"stdev"` | Spatial standard deviation among pixels | How heterogeneous METREF is within the zone |
| `"count"` | Effective raster-cell coverage contributing to the polygon | Useful as a support/QC diagnostic |
| `"quantile(q=0.10)"` | Spatial 10th percentile | Low-end conditions within the polygon |
| `"quantile(q=0.90)"` | Spatial 90th percentile | High-end conditions without using the single maximum |



> **How spatially variable was half-month mean METREF within each spatial unit?**

Blue/low values mean the polygon is relatively homogeneous. Higher/red values mean stronger within-zone spatial variability for that specific time.

---

# 3. Important distinction: `metref_mean` vs zonal `"mean"`

This can be confusing because we have both.

climate-processing stage produced something like:

```text
metref_mean
metref_min
metref_max
metref_p90
metref_anomaly
metref_anomaly_z
```

These are primarily **temporal summaries at each pixel**.

Then Xvec does:

```text
mean
min
max
median
stdev
p10
p90
```

across the pixels inside each polygon.

So:

```python
variable="metref_max"
statistic="mean"
```

means:

> Average across the zone of each pixel's **maximum daily METREF during that half-month**.

While:

```python
variable="metref_mean"
statistic="max"
```

means:

> The **highest spatial pixel value** of half-month mean METREF anywhere inside that zone.

Those are quite different.

---

# 4. For mobility analysis

You do **not** need every possible combination.

For final zone × time table, concentrate on these:

| Climate variable | Zonal statistic | Why |
|---|---|---|
| `metref_mean` | `mean` | Main atmospheric-demand exposure |
| `metref_mean` | `stdev` | Within-zone environmental heterogeneity |
| `metref_mean` | `quantile(q=0.90)` | High-exposure portion of the zone |
| `metref_max` | `mean` | Typical extreme daily demand across zone |
| `metref_anomaly` | `mean` | Average departure from climatology |
| `metref_anomaly_z` | `mean` | Best standardized climate anomaly for cross-region comparison |
| `high_demand_days` | `mean` | Typical number of high-demand days across the zone |

For the main climate–mobility models, I would start with:

```text
zonal mean anomaly
zonal mean standardized anomaly
high-demand days
spatial stdev
```

The first three describe climate exposure; `stdev` tells you whether the zone itself is environmentally heterogeneous.

---

# 5. Plot the same variable using different zonal statistics

Mean:

```python
plot_metref_maps(
    stats,
    variable="metref_mean",
    statistic="mean",
    metref_cmap=metref_cmap,
    time_index=slice(0, 10),
)
```

Spatial variability:

```python
plot_metref_maps(
    stats,
    variable="metref_mean",
    statistic="stdev",
    metref_cmap=metref_cmap,
    time_index=slice(0, 10),
)
```

High spatial percentile:

```python
plot_metref_maps(
    stats,
    variable="metref_mean",
    statistic="quantile(q=0.90)",
    metref_cmap=metref_cmap,
    time_index=slice(0, 10),
)
```

This gives you three different questions:

```text
mean   → What is typical?
stdev  → How heterogeneous is the zone?
p90    → How high are conditions in the more exposed parts?
```

---

# 6. When to use scaling

For your raw METREF maps, normally use:

```python
scale=None
```

because you want the original physical units.

For comparing relative temporal behaviour:

```python
scale="zscore"
```

For example:

```python
plot_metref_maps(
    stats,
    variable="metref_mean",
    statistic="mean",
    metref_cmap=metref_cmap,
    scale="zscore",
    periods=[
        "2010-01-01",
        "2010-01-16",
        "2010-02-01",
        "2010-02-16",
    ],
)
```

This asks:

> Is each zone unusually high or low relative to its own temporal behaviour?

For dashboards:

```python
scale="minmax"
```

puts everything on:

```text
0 ───────────── 1
low              high
```

but I would prefer z-scores for scientific interpretation.

---

# 7. `plot_zone_timeseries()`

Use this when you have **one variable and want to compare several places through time**.

For example:

```python
plot_zone_timeseries(
    stats,
    variable="metref_mean",
    statistic="mean",
    cities=[
        "Dakar",
        "Kaolack",
        "Tambacounda",
    ],
)
```

Question answered:

> How does METREF evolve through time in these different areas?

To compare temporal patterns rather than absolute magnitude:

```python
plot_zone_timeseries(
    stats,
    variable="metref_mean",
    statistic="mean",
    cities=[
        "Dakar",
        "Kaolack",
        "Tambacounda",
    ],
    scale="zscore",
    scale_scope="per_series",
)
```

Then every city has approximately:

```text
0 = its own normal
+1 = one standard deviation above normal
-1 = one standard deviation below normal
```

Your original plotting module was already designed around filtering cities/zones before plotting their temporal series. Pasted markdown

---

# 8. `plot_zone_variables()`

Use this for the opposite question:

> **One place, several variables.**

For example:

```python
plot_zone_variables(
    combined_stats,
    zone="Kaolack",
    variables=[
        "metref_mean",
        "ndvi_mean",
        "soil_moisture_mean",
        "precipitation_sum",
    ],
    statistic="mean",
    scale="zscore",
)
```

This is where standardization is especially useful because otherwise you would compare:

```text
METREF          different units
NDVI            0–1
soil moisture   another scale
precipitation   mm
```

After z-scoring, you can inspect whether:

```text
METREF rises
       ↓
soil moisture falls
       ↓
NDVI later declines
       ↓
mobility changes
```

This will be especially useful once you combine your climate cube and mobility table.

---

## My practical plotting sequence

For every new climate variable, I would follow this order:

**First:** raw spatial mean

```python
variable="metref_mean"
statistic="mean"
scale=None
```

**Second:** spatial heterogeneity

```python
statistic="stdev"
```

**Third:** anomaly

```python
variable="metref_anomaly_z"
statistic="mean"
vmin=-3
vmax=3
```

**Fourth:** several zones through time

```python
plot_zone_timeseries(...)
```

**Fifth:** climate variables together for one zone

```python
plot_zone_variables(
    ...,
    scale="zscore"
)
```

logical progression:

> **Where? → How variable spatially? → How abnormal? → How does it change through time? → How does it relate to other climate/mobility variables?**



- Check normal distribution for the data
