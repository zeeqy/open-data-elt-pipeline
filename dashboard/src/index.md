---
title: Fuel, ridership & prices
toc: true
---

```js
const weekly = FileAttachment("data/weekly.csv").csv({typed: true});
const monthly = FileAttachment("data/monthly.csv").csv({typed: true});
const lagCorr = FileAttachment("data/lag_corr.csv").csv({typed: true});
const cpiPeriods = FileAttachment("data/cpi_periods.csv").csv({typed: true});
const recovery = FileAttachment("data/recovery.csv").csv({typed: true});
const meta = FileAttachment("data/meta.json").json();
```

```js
const pct = d3.format("+.1%");
const pct0 = d3.format(".0%");
const num = d3.format(",.0f");
const r2 = d3.format("+.3f");
const rm = (v) => `RM ${d3.format(".2f")(v)}`;
const monthName = d3.utcFormat("%b %Y");
const dayName = d3.utcFormat("%-d %b %Y");

const withRiders = monthly.filter((d) => d.avg_weekday_rail_riders != null);
const lastRidership = withRiders.at(-1);
const lastCpi = monthly.filter((d) => d.cpi_transport_yoy_pct != null).at(-1);
const lastYear = recovery.at(-1);
const strongestLag = d3.greatest(lagCorr, (d) => Math.abs(d.r));
const recent = cpiPeriods.find((d) => d.period === "2022-now");
const early = cpiPeriods.find((d) => d.period === "2018-2021");
const bigMoves = weekly.filter(
  (d) => d.week_start >= new Date("2023-01-02") && Math.abs(d.ron97_wow_pct) >= 0.03
).length;
```

# Do fuel prices move Klang Valley public transport?

Daily Rapid KL rail ridership, weekly pump prices, monthly CPI and BNM's USD/MYR rate, loaded every morning from Malaysian open data. Data up to: ridership **${dayName(new Date(meta.latest.ridership))}**, fuel **${dayName(new Date(meta.latest.fuel))}**, CPI **${monthName(new Date(meta.latest.cpi))}**.

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Weekday rail riders</h2>
    <span class="big">${num(lastRidership.avg_weekday_rail_riders)}</span>
    <div class="muted">avg per weekday, ${monthName(lastRidership.month_start)}, Rapid KL rail</div>
  </div>
  <div class="card">
    <h2>vs 2019, same lines</h2>
    <span class="big">${pct0(lastYear.pct_of_2019 / 100)}</span>
    <div class="muted">${lastYear.year} year to date, lines open in 2019</div>
  </div>
  <div class="card">
    <h2>RON97</h2>
    <span class="big">${rm(meta.fuel_now.ron97)}</span>
    <div class="muted">per litre, since ${dayName(new Date(meta.fuel_now.effective_date))} (diesel ${rm(meta.fuel_now.diesel)})</div>
  </div>
  <div class="card">
    <h2>Transport CPI</h2>
    <span class="big">${pct(lastCpi.cpi_transport_yoy_pct / 100)}</span>
    <div class="muted">year on year, ${monthName(lastCpi.month_start)} (overall ${pct(lastCpi.cpi_overall_yoy_pct / 100)})</div>
  </div>
</div>

## 1. Do fuel price changes move ridership?

**No visible link.** Since 2023, the weekly change in weekday rail riders has almost no correlation with the change in RON97, in the same week or up to 4 weeks later: the strongest is r = ${r2(strongestLag.r)} at a lag of ${strongestLag.lag_weeks} week(s), over ${strongestLag.weeks} weeks. RON97 moved by 3% or more in ${bigMoves} of those weeks, so there was variation to detect.

The likely reason is who pays it. Most drivers buy subsidised RON95, which was a flat RM 2.05 until September 2025 and RM 1.99 (BUDI95) since: its citizen price took only two values in this period. RON97 is the free-floating price, but few commuters buy it.

```js
Plot.plot({
  height: 320,
  grid: true,
  x: {label: "RON97 price change that week →", tickFormat: "+.0%"},
  y: {label: "↑ Change in avg weekday rail riders", tickFormat: "+.0%"},
  marks: [
    Plot.ruleX([0]),
    Plot.ruleY([0]),
    Plot.dot(
      weekly.filter((d) => d.week_start >= new Date("2023-01-02") && d.weekdays_reported === 5),
      {x: "ron97_wow_pct", y: "riders_wow_pct", r: 3, fillOpacity: 0.6, fill: "steelblue",
       tip: true, title: (d) => `Week of ${dayName(d.week_start)}\nRON97 ${pct(d.ron97_wow_pct)}\nRiders ${pct(d.riders_wow_pct)}`}
    )
  ]
})
```

```js
Plot.plot({
  height: 180,
  x: {label: "RON97 change this many weeks before →"},
  y: {label: "↑ Correlation r", domain: [-1, 1], grid: true},
  marks: [
    Plot.ruleY([0]),
    Plot.barY(lagCorr, {x: "lag_weeks", y: "r", fill: "steelblue", tip: true}),
    Plot.text(lagCorr, {x: "lag_weeks", y: "r", text: (d) => d3.format("+.2f")(d.r), dy: -8})
  ]
})
```

<div class="note">Correlation of week-on-week changes, full 5-weekday weeks only. Holiday weeks (Raya, CNY, school breaks) add noise. This is a check for an obvious effect, not proof that none exists.</div>

## 2. Does transport inflation follow fuel prices?

**Yes, but weakly since 2022.** From 2018 to 2021, when RON95 itself floated, transport CPI tracked it almost one for one (r = ${r2(early.r_ron95_citizen)}). Since 2022, citizen RON95 barely moved (its year-on-year change has a standard deviation of only ${d3.format(".1f")(recent.ron95_yoy_sd)} points), and transport CPI follows RON97 instead (r = ${r2(recent.r_ron97)}), with a small effect: each 1 point of RON97 year-on-year inflation goes with about ${d3.format(".2f")(recent.cpi_pts_per_ron97_pt)} points of transport CPI inflation.

```js
const yoy = monthly
  .filter((d) => d.month_start >= new Date("2018-03-01") && d.cpi_transport_yoy_pct != null)
  .flatMap((d) => [
    {month: d.month_start, series: "Transport CPI", value: d.cpi_transport_yoy_pct},
    {month: d.month_start, series: "RON97", value: d.ron97_yoy_pct},
    {month: d.month_start, series: "RON95 (citizen price)", value: d.ron95_citizen_yoy_pct}
  ]);
```

```js
Plot.plot({
  height: 340,
  marginRight: 110,
  grid: true,
  color: {legend: true, domain: ["Transport CPI", "RON97", "RON95 (citizen price)"], range: ["#d62728", "#1f77b4", "#9aa5b1"]},
  facet: {data: yoy, y: (d) => (d.series === "Transport CPI" ? "Transport CPI" : "Pump prices"), label: null},
  fy: {domain: ["Transport CPI", "Pump prices"]},
  x: {label: null},
  y: {label: "↑ Year-on-year change (%)"},
  marks: [
    Plot.ruleY([0]),
    Plot.lineY(yoy, {x: "month", y: "value", stroke: "series", tip: true}),
    Plot.ruleX([new Date("2022-01-01")], {stroke: "#888", strokeDasharray: "4,3"})
  ]
})
```

<div class="note">The dashed line marks the split used for the two correlations. Year-on-year changes, monthly averages of weekly prices. Transport CPI covers far more than fuel (cars, fares, maintenance).</div>

## 3. Has rail ridership recovered from COVID?

**Yes, and it is now above 2019.** On the rail lines that already ran in January 2019 (${lastYear.lines.split(" ").length} lines), average weekday ridership in ${lastYear.year} is ${pct0(lastYear.pct_of_2019 / 100)} of the 2019 level, after falling to ${pct0(d3.min(recovery, (d) => d.pct_of_2019) / 100)} in ${d3.least(recovery, (d) => d.pct_of_2019).year}. Counting newer lines as well, Rapid KL rail now carries about ${num(lastRidership.avg_weekday_rail_riders)} people on an average weekday.

```js
Plot.plot({
  height: 260,
  y: {label: "↑ Avg weekday riders, % of 2019 (same lines)", domain: [0, 130], grid: true},
  x: {label: null, tickFormat: "d"},
  marks: [
    Plot.barY(recovery, {x: "year", y: "pct_of_2019", fill: (d) => (d.pct_of_2019 >= 100 ? "#2ca02c" : "#9aa5b1"), tip: true}),
    Plot.ruleY([100], {stroke: "#333", strokeDasharray: "4,3"}),
    Plot.text(recovery, {x: "year", y: "pct_of_2019", text: (d) => `${d3.format(".0f")(d.pct_of_2019)}%`, dy: -8})
  ]
})
```

Weekends recovered faster than weekdays: weekend riders were about ${pct0(d3.mean(withRiders.filter((d) => d.month_start.getUTCFullYear() === 2019), (d) => d.avg_weekend_rail_riders / d.avg_weekday_rail_riders))} of weekday riders in 2019 and about ${pct0(d3.mean(withRiders.filter((d) => d.month_start.getUTCFullYear() === lastYear.year), (d) => d.avg_weekend_rail_riders / d.avg_weekday_rail_riders))} in ${lastYear.year}. That fits more leisure trips by train, or more work from home on weekdays, but the data cannot say which.

```js
const dayType = withRiders.flatMap((d) => [
  {month: d.month_start, type: "Weekday", riders: d.avg_weekday_rail_riders},
  {month: d.month_start, type: "Weekend", riders: d.avg_weekend_rail_riders}
]);
```

```js
Plot.plot({
  height: 280,
  grid: true,
  color: {legend: true, domain: ["Weekday", "Weekend"], range: ["#1f77b4", "#ff7f0e"]},
  y: {label: "↑ Avg daily riders, all Rapid KL rail lines", tickFormat: "~s"},
  x: {label: null},
  marks: [Plot.lineY(dayType, {x: "month", y: "riders", stroke: "type", tip: true})]
})
```

<div class="note">Rapid KL rail = LRT Ampang/Sri Petaling, LRT Kelana Jaya, LRT Shah Alam, MRT Kajang, MRT Putrajaya and the KL Monorail. The line chart includes lines as they open (MRT Putrajaya 2022-23, LRT Shah Alam 2026), so its rise is partly new capacity; the bar chart above does not.</div>
