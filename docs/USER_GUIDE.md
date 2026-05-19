# User Guide — HydroServer Quality Control App

This guide is for the operator: the hydrologist or technician who picks a
datastream, marks the bad points, and submits the cleaned series back to
HydroServer. It walks through every feature on the screen and the
shortest path to common QC tasks.

If you are looking for developer / deployment docs, start with
[ARCHITECTURE.md](./ARCHITECTURE.md) instead.

## What this app does

The QC App is the operator's view of HydroServer's quality control
pipeline. With it you can:

1. **Browse** sites and datastreams in a HydroServer workspace.
2. **Plot up to five datastreams** on a synchronized multi-axis chart for
   visual context.
3. **Pick one datastream as the QC target** — the rest are read-only
   reference traces.
4. **Filter** suspicious points using value thresholds, time windows,
   change detection, gap detection, or persistence runs.
5. **Edit** the selected points: change values, interpolate, drift-
   correct, shift datetimes, delete, fill gaps, add points.
6. **Save your edits as a QC script** — a JSON file you can replay on
   the same or another datastream later.
7. **Submit** the cleaned observations back to HydroServer.

Everything runs in your browser. The backend never sees your edit
history until you press Submit.

## Glossary

| Term | Meaning |
|------|---------|
| **Workspace** | A HydroServer scope (one organization or project's data). You pick one when you sign in. |
| **Thing / Site** | A physical site or sampling location. |
| **Datastream** | A single time-series at a site: one variable, one sensor, one processing level. |
| **Observation** | A single (timestamp, value) measurement. |
| **QC target** | The datastream you are editing. There is always exactly one QC target when the Edit drawer is open. |
| **Context traces** | The other plotted datastreams. Visible but read-only — they exist to give you context for the QC target. |
| **History** | The ordered list of filters + edits you've applied in the current session. Undo / redo / save / load all operate on this list. |
| **Selection** | The set of point indices a filter (or your click / lasso) produced. Edits operate on the current selection. |
| **QC script** | A JSON file holding your history. Reusable across datastreams; the canonical save format. |
| **Submit** | POST the cleaned observations back to HydroServer with `mode=replace`. This overwrites the existing observations in the window you have plotted. |

## First-time setup

1. Open the app URL. It will redirect you to **Login**.
2. Sign in with your HydroServer email + password, or click **Sign in with
   Google** if your deployment has Google OAuth enabled.
3. On the **Workspaces** page, pick the workspace you want to work in.
   The choice is remembered locally — next time you sign in you'll land
   directly on the Home screen.
4. On **Home**, the left filter drawer is open. Pick a time range and
   filter the datastream list by site / observed property / processing
   level.

If the screen ever stays blank with a console error like `Failed to
fetch app settings`, ask your administrator to check the API URL and
COOP/COEP configuration ([DEPLOYMENT.md](./DEPLOYMENT.md) covers this).

## The screen, top to bottom

```
┌───────────────────────────────────────────────────────────────────┐
│ ┌──────┐ ┌─────────────────┐ ┌─────────────────────────────────┐  │
│ │ Nav  │ │ Select drawer   │ │ Plot + table                    │  │
│ │ rail │ │  (Time range)   │ │                                 │  │
│ │      │ │  (Filters)      │ │                                 │  │
│ │ home │ │                 │ │                                 │  │
│ │ edit │ │                 │ │                                 │  │
│ │ ...  │ └─────────────────┘ │                                 │  │
│ │ wks  │                     └─────────────────────────────────┘  │
│ │ out  │                                                          │
│ └──────┘                                                          │
└───────────────────────────────────────────────────────────────────┘
```

### Navigation rail (far left)

A thin, always-visible column of icons.

| Icon | Action |
|------|--------|
| HydroServer logo | Go home. Resets the current view. Prompts before discarding unsaved edits. |
| Cursor (Select) | Show the Select drawer + plot. |
| Pencil (Edit) | Open the Edit drawer. **Disabled** until you've picked a QC datastream. |
| Stopwatch (Performance) | Open the Performance Calibration dialog. See "Performance" below. |
| Grid (Workspace) | Switch workspace. |
| Logout | Sign out. |

If you click any of these while you have unsaved edits in the Edit
view, the app shows a confirmation dialog with **Save & continue** /
**Discard** / **Cancel**. Discarded edits cannot be recovered.

### Select drawer

The left drawer in the default view, with two collapsible sections:

- **Time range** — preset buttons (1w, 1m, 6m, 1y, **All**) and a custom
  date picker. The chosen window is what gets fetched from the backend
  for any newly plotted datastream.
  - **Tip:** when previewing a brand-new datastream whose observations
    might be years old, click **All** first. The default `1w` preset can
    show an empty window for old data and make the plot look broken.
- **Datastream filters** — pick the site, observed property, and
  processing level. The list of matching datastreams updates live.

Click a datastream row to plot it. Click again to unplot.

The drawer is **resizable** — drag the right edge — and **collapsible**
via the chevron at the top.

### Plot + data table

The main work area. By default:

- The top half is the Plotly chart with a synchronized x-axis and one
  y-axis per plotted datastream.
- The bottom half is the **Data table** — the observations for the QC
  target as rows. You can edit values directly in the table; edits flow
  through the same dispatch path as the edit panels and append to
  history.

Tools at the top of the plot:

- **Zoom** (drag a horizontal box on the x-axis)
- **Pan** (hold + drag)
- **Box select / Lasso select** (the dashed-rectangle and lasso buttons
  in the Plotly toolbar) — these are the primary way to select points
  for an edit.
- **Reset axes** — back to the full plotted window.

Clicking a single point selects just that point. Selecting nothing on
the plot clears the selection.

The first datastream you plot becomes the **QC target**. You can change
the QC target by reordering the plotted-datastreams list (the
**Plotted Datastreams** card at the right of the Visualize view).

### Edit drawer

Opens when you click the pencil icon in the nav rail (only enabled
after you've picked a QC datastream). The drawer is a vertical column
of operation icons; clicking one expands a panel with that op's inputs.

Three operation groups, color-coded the same way in the **Edit History**
panel:

- **Filter** (blue) — operations that *flag* points without changing
  values. They produce a selection.
- **Edit** (blue / amber) — operations that change values or timestamps
  at the current selection. Amber edits need a selection first.
- **Add** (green) — operations that insert new points (Add Points, Fill
  Gaps) or attach qualifiers without changing values.

## The QC operations, one by one

### Filter operations

These do not change data. They produce a selection that the next edit
operation acts on.

#### Value thresholds

Flag any point outside a min / max range. Configure greater-than,
less-than, equal-to, and combinations.

> **Example:** "Anything reading > 100 mg/L is bad" → set
> `Greater than: 100` and run. Every offending point is now selected.

#### Datetime range

Select every point within a specific datetime window. Useful when you
know a sensor was down between two timestamps and want to flag the
whole interval.

#### Change threshold

Flag pairs of adjacent points whose value delta exceeds a threshold.
Catches sudden spikes / drops that violate physical plausibility.

#### Rate of change

Like Change but normalized to value change per unit time. The threshold
is expressed as a fraction (e.g. `0.5` = 50% change).

#### Find gaps

Locate gaps in time between consecutive observations that exceed a
threshold (e.g. ">15 minutes"). The gap intervals get added to the
selection.

#### Persistence

Flag **runs** of identical repeated values (e.g. the sensor stuck on
the same reading for 30 minutes). Configure the minimum run length.

### Edit operations

These change values or timestamps at the current selection. The amber
ones require you to make a selection first; the drawer disables them
until you do.

#### Drift correction

Apply a linear drift correction across each consecutive group in the
selection. Use this when a sensor has drifted from a known reference.

#### Interpolate

Replace each consecutive group in the selection with linearly
interpolated values from the surrounding good points.

#### Change values

Apply an operator (ADD / SUB / MULT / DIV / ASSIGN) at each selected
index.

#### Shift datetimes

Offset the selection's timestamps by a duration (e.g. -1 hour). Useful
when a sensor's clock was off.

#### Delete points

Drop the selected points from the series entirely.

### Add operations

#### Qualifying comments

Attach qualifier flags (e.g. "estimated", "ice-affected") to selected
points. The selected qualifier set lives in the workspace's qualifier
list, configured upstream in HydroServer.

> **Note:** qualifier codes are tracked locally but not yet serialized
> to the backend on Submit. See [QUALITY.md](./QUALITY.md) for the
> status.

#### Add points

Insert one or more (datetime, value) tuples. The plot stage marker lets
you drag onto the chart to place points visually, or you can type
values directly into the panel.

#### Fill gaps

Detect gaps over a threshold and fill them with interpolated values or
a constant fill value at a chosen cadence.

> **Workflow:** combine with **Find gaps**. Run Find gaps to see them
> highlighted, eyeball whether they're real outages, then run Fill gaps
> to interpolate.

## The Edit History panel

Every filter, edit, and add operation appends a row to the **Edit
History** at the bottom of the Edit drawer. Each row shows:

- The operation icon and name.
- A success / failure indicator.
- The duration in ms.
- In dev mode, a small badge showing whether the op ran inline or on a
  worker.

You can:

- **Undo** — pops the most recent op off the history and replays from
  scratch (so undo of "Interpolate" rewinds the interpolated values
  back to whatever the selection's original values were).
- **Redo** — re-pushes the most recently undone op.
- **Remove a specific history entry** — useful if you applied an op by
  mistake and have piled more edits on top. The history is replayed
  without the removed entry.

The history is reset when you change the QC datastream, navigate away
without saving, or click **Submit** (success clears the history).

## Save / load a QC script

The QC script is the canonical save format. It's a JSON file you can
keep, re-apply, share, or version-control.

### Save

In the Edit drawer, click **Export script**. The browser downloads a
file named like:

```
qc-script-<datastream-name>-<isoTimestamp>.json
```

The file contains:

- The wall-clock window of the plotted data.
- Every operation in the history, in order, with its args.

### Load

In the Edit drawer, click **Import script** and pick a JSON file. The
app will:

1. Fetch the script's authored window into your current QC datastream
   (the indices in selection-coupled ops reference the *windowed*
   dataset, so the window has to match).
2. Replay each operation in order.
3. Show a Snackbar with `applied: N` and any per-op failures.

Per-op failures do not abort the replay — the app keeps going. If your
script targets columns that don't exist in the new datastream (e.g. a
qualifier code that isn't registered), that specific op will fail and
be visible in the history with a red status, but the rest still run.

### When to use it

- **Repeatable QC.** Apply the same QC routine across all your
  conductivity sensors with one script.
- **Audit trail.** Save the script before submitting — you have a
  record of every transformation you applied.
- **Iterate offline.** Edit the script's JSON if you want to tweak a
  threshold without re-clicking through the panels.

## Submit

When you're satisfied with the edits:

1. Click **Submit** in the Edit drawer.
2. The app POSTs the cleaned observations to HydroServer with
   `mode: 'replace'` — this overwrites the existing observations in the
   plotted window.
3. On success, the Snackbar shows "Quality-controlled observations
   submitted" and the local history is cleared.
4. On failure, the Snackbar shows the backend's error message verbatim
   — show that to your administrator if you need help.

> **Warning:** Submit is **destructive on the backend** — it replaces
> the observations in the plotted window. If you might want to revert,
> export a QC script *before* submitting and keep the original raw
> observations separately. The QC App itself can't undo a Submit.

## Performance and big datastreams

For datastreams with hundreds of thousands of points:

- The first **All**-range fetch takes a while (paginated at 50,000 obs
  per page). The Snackbar shows a per-stream loading indicator.
- Long-running operations run on web workers when available, so the UI
  stays responsive. If your browser doesn't support
  `SharedArrayBuffer` (or the deployment dropped the COOP/COEP
  headers), operations run inline and a particularly large edit may
  freeze the UI for a moment. The result is identical either way.
- The **Performance Calibration** dialog (stopwatch icon in the nav
  rail) shows the measured worker / inline throughput on your device
  and lets you re-benchmark on demand. If big edits feel slower than
  they used to (e.g. after you upgraded your OS), re-benchmark.

See [PERFORMANCE.md](./PERFORMANCE.md) for the envelope details.

## Common tasks

### "I just want to drop everything above 1000 and re-submit."

1. Pick a workspace, then pick the datastream you want to QC.
2. Plot it (it becomes the QC target).
3. Click **All** in the Time range so you load the full series.
4. Click the pencil icon → expand **Value thresholds**, set
   `Greater than: 1000`, click Run.
5. Expand **Delete points**, click Run.
6. Click **Submit**.

### "I want to drift-correct a known-bad interval."

1. Plot the datastream. Zoom in to the bad interval on the chart.
2. Drag a box select around the interval.
3. Open the Edit drawer → **Drift correction** → set the drift value
   (the offset to apply linearly from start to end of the selection) →
   Run.
4. Inspect the result on the chart. Undo if it's wrong.
5. Submit when satisfied.

### "I want to replay last week's QC on this week's data."

1. Load the new week of data on the same datastream.
2. Open the Edit drawer → **Import script** → pick last week's JSON.
3. The script's authored window may differ from this week's — the app
   will fetch the script's window. To re-apply against the new window
   instead, save the new window first, edit the script's `window` field
   in a text editor, then re-import.
4. Review the history. Submit.

### "I picked the wrong workspace."

Click the grid icon in the nav rail → pick another. If you have
unsaved edits, the app asks first.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Blank page on load | Wrong API URL or `localhost` vs `127.0.0.1` mismatch. | See [DEPLOYMENT.md](./DEPLOYMENT.md). |
| Plot stays empty after picking a datastream | Time range falls outside the datastream's observations. | Click **All** in Time range. |
| "Edit" icon is greyed out | No QC datastream selected. | Plot at least one datastream — the first becomes the QC target. |
| Big edits freeze the page | `SharedArrayBuffer` not available; running inline. | Have your admin re-enable COOP/COEP headers, or accept the slower fallback. |
| Submit fails with a backend error | Permissions / workspace issue / network. | The Snackbar shows the backend message verbatim — share that with your admin. |
| The history shows a red failed entry after Import | The script referenced something missing in this datastream. | The rest of the script still ran; check the offending entry's tooltip. |

## See also

- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md) — what's running behind the screen
- HydroServer documentation: <https://hydroserver2.github.io/hydroserver/>
