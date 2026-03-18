# HydroServer Manual Release Testing Checklist

This document covers release testing items that cannot be reliably automated with
Playwright. Items are grouped by app section. Work through this checklist before
each production release alongside the automated e2e suite.

---

## Section 2 — Browse / Map Page

- [ ] **Map marker click** — click a marker on the OpenLayers map and confirm the
      site popup appears with the correct site name and a "View site details" link.
- [ ] **Popup site details link** — confirm the link in the popup navigates to the
      correct `/sites/<id>` page.
- [ ] **Map zoom / pan controls** — use the on-map zoom buttons and confirm the
      map zooms in and out without error.

---

## Section 3 — Authentication

- [ ] **Google OAuth login** — click "Sign in with Google", complete the Google
      auth flow, and confirm the user lands on `/sites` as the correct account.
- [ ] **UtahID OAuth login** — click "Sign in with UtahID", complete the UtahID
      auth flow, and confirm the user lands on `/sites` as the correct account.
- [ ] **OAuth account creation** — sign up via OAuth for the first time and
      confirm a new account is provisioned with an onboarding prompt.

---

## Section 5 — Workspace Transfers

- [ ] **Accept a workspace transfer** — log in as the destination user, open the
      pending transfer dialog, click "Accept transfer", and confirm the workspace
      now appears in the destination user's workspace list and is removed from the
      source user's list.
- [ ] **Cancel a workspace transfer** — log in as the destination user, open the
      pending transfer dialog, click "Cancel transfer", and confirm the workspace
      remains with the source user.

---

## Section 7 — Site Details / Datastreams

- [ ] **Load Template button** — on the "Add datastream" form, click "Load
      Template", select an existing orchestration template, and confirm the form
      pre-fills with the template's field values.
- [ ] **Sparkline color coding** — for a datastream with recent data confirm the
      sparkline displays in green (or the active color); for a datastream with only
      old data confirm the sparkline displays in grey (or the stale color).
- [ ] **Sparkline data point density** — sub-daily datastreams should render
      approximately 200 points; daily datastreams should render approximately 50
      points. Visually verify both cases.
- [ ] **Popup plot — time range buttons** — click a datastream sparkline to open
      the popup plot. Click "Last Week", "Last Month", and "Last Year" buttons and
      confirm the visible date range on the plot updates accordingly.
- [ ] **Popup plot — brush / zoom** — drag on the popup plot to brush-select a
      time range and confirm the main plot zooms in. Scroll on the plot and confirm
      zooming works.
- [ ] **Delete data from a datastream** — open the Actions menu for a datastream
      that has data, click "Delete data", confirm the deletion dialog, and verify
      the datastream now shows no observation count.

---

## Section 8 — Visualize Data

- [ ] **Plot brush / zoom** — drag on the Plotly chart to zoom into a time range.
      Confirm the axes update. Click "Reset zoom" and confirm the axes return to
      the full range.
- [ ] **Show / hide columns** — toggle the column visibility control (if present)
      and verify that selected columns appear and disappear from the datastream
      table.

---

## Section 11 — Job Orchestration

- [ ] **Add new data source** — click "Add data source" (or equivalent), fill in
      the required connection fields, save, and confirm the new data source appears
      in the list.
- [ ] **Add new task** — with a data source selected, click "Add task", fill in
      the task fields, save, and confirm the task appears under the data source.
- [ ] **Run Now** — click "Run Now" on an existing task and confirm the task
      status updates to a running or queued state (or a success toast appears).
- [ ] **Pause / Resume** — click "Pause" on a running task and confirm the status
      changes to paused. Click "Resume" and confirm it returns to active.
- [ ] **Manage data connections** — click "Manage data connections", edit a
      connection's credentials, save, and confirm no error is shown.
