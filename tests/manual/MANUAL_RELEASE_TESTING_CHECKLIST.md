# HydroServer Manual Release Testing Checklist

This document is for release checks that are still outside the deterministic CI
gate. If a workflow can be exercised reliably in local fixtures or in
Playwright, it should move out of this checklist and into automation.

Automated coverage now handles the repeatable release checks for workspace CRUD
and transfers, site registration and CRUD, datastream CRUD and privacy-control
persistence, metadata CRUD and deletion guards, visualization filters/search/
downloads/state restore, orchestration workspace selection, and backend
enforcement for hidden datastream observations.

Work through this list before production release alongside CI.

---

## Section 2 — Browse / Map Page

- [ ] **Browse filter-to-map behavior** — apply Browse page filters and confirm
      the visible markers/popups match the selected filters on the map.
- [ ] **Map marker click** — click a marker on the OpenLayers map and confirm the
      site popup appears with the correct site name and a "View site details" link.
- [ ] **Popup site details link** — confirm the link in the popup navigates to the
      correct `/sites/<id>` page.
- [ ] **Map zoom / pan controls** — use the on-map zoom buttons and confirm the
      map zooms in and out without error.

---

## Section 3 — Authentication

- [ ] **Email verification sign-up** — create a username/password account,
      confirm a verification email is received, activate the account, and verify
      the first login lands on `/sites`.
- [ ] **Google OAuth login** — click "Sign in with Google", complete the Google
      auth flow, and confirm the user lands on `/sites` as the correct account.
- [ ] **UtahID OAuth login** — click "Sign in with UtahID", complete the UtahID
      auth flow, and confirm the user lands on `/sites` as the correct account.
- [ ] **OAuth account creation** — sign up via OAuth for the first time and
      confirm a new account is provisioned with an onboarding prompt.

---

## Section 5 — Workspace Transfers

- [ ] **Pending-transfer permissions** — while the transfer is pending, confirm
      the destination user can see the workspace sites but cannot edit them.

---

## Section 6 — Your Sites / Workspace Maps

- [ ] **Map extent / zoom behavior** — open `Your Sites`, switch between
      workspaces, and verify the map zooms to the extent of the visible sites.
- [ ] **Collaborator access verification** — after adding or changing a
      collaborator role, log in as that collaborator and confirm the resulting
      access matches the assigned role.
- [ ] **Site photo drag-and-drop** — create or edit a site using drag-and-drop
      photo upload and confirm the image is persisted and visible on the site
      details page.

---

## Section 7 — Site Details / Datastreams

- [ ] **Site-details map interaction** — interact with the map on the site
      details page and confirm marker/location behavior remains correct.
- [ ] **Private site Browse visibility** — toggle a site between public and
      private and confirm anonymous or unauthorized users stop seeing it on the
      Browse monitoring sites page until it is made public again.
- [ ] **Load Template button** — on the "Add datastream" form, click "Load
      Template", select an existing orchestration template, and confirm the form
      pre-fills with the template's field values.
- [ ] **Rating curve manager CRUD** — on a site details page, open "Manage rating
      curves", add a CSV-backed rating curve, confirm its preview/details render,
      update its description or file, download it, and delete it successfully.
- [ ] **Rating curve delete guard** — attach a site rating curve to an
      orchestration task, then return to the site's rating curve manager and
      confirm deletion is blocked with links to the referencing task(s).
- [ ] **Datastream form auto-fill controls** — verify any auto-fill controls on
      the datastream form populate fields with the expected values.
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

- [ ] **Multi-series plot correctness** — select multiple datastreams and verify
      each series renders with a distinct color/axis and that the axes auto-scale
      sensibly.
- [ ] **Plot brush / zoom** — drag on the Plotly chart to zoom into a time range.
      Confirm the axes update. Click "Reset zoom" and confirm the axes return to
      the full range.
- [ ] **Plot PNG export** — download the plot image and confirm a valid PNG is
      produced for the currently displayed chart state.

---

## Section 10 — Streaming Data Loader

- [ ] **SDL installation and registration** — install SDL, connect it to the
      HydroServer instance, and confirm the orchestration system appears in the UI.
- [ ] **SDL authentication modes** — verify both username/password and API-key
      based loading paths work.
- [ ] **SDL multi-workspace support** — configure SDL against multiple workspaces
      and confirm each workspace behaves correctly.

---

## Section 11 — Job Orchestration

- [ ] **Add new data source** — click "Add data source" (or equivalent), fill in
      the required connection fields, save, and confirm the new data source appears
      in the list.
- [ ] **Schedule controls** — verify schedule fields such as start time,
      interval, and any Local/UTC toggles behave correctly.
- [ ] **Data source details view** — open an existing data source and confirm its
      details render correctly.
- [ ] **Edit / delete data source** — update a data source, save the changes, then
      delete a disposable one and confirm both actions persist.
- [ ] **Payload mapping CRUD** — add mappings/payloads, edit them, delete them,
      and confirm the saved configuration matches the changes.
- [ ] **Add new task** — with a data source selected, click "Add task", fill in
      the task fields, save, and confirm the task appears under the data source.
- [ ] **Rating curve transformation workflow** — edit or create an ETL task,
      add a rating curve transformation to a mapping, verify both "Select existing
      rating curve" and "Create new rating curve" flows work, confirm the preview
      loads, save the task, then reopen it and verify the selected rating curve
      persists.
- [ ] **Aggregation task create/edit workflow** — create an Aggregation task
      without a data connection, choose source and target datastreams, set an
      aggregation statistic, verify both fixed-offset and daylight-savings-aware
      timezone modes work, save, then reopen the task and confirm the mappings and
      timezone settings persist.
- [ ] **Aggregation task validation states** — while creating or editing an
      Aggregation task, confirm missing source datastream, target datastream, or
      aggregation statistic fields show validation errors and block save until the
      task is completed correctly.
- [ ] **Run Now** — click "Run Now" on an existing task and confirm the task
      status updates to a running or queued state (or a success toast appears).
- [ ] **Pause / Resume** — click "Pause" on a running task and confirm the status
      changes to paused. Click "Resume" and confirm it returns to active.
- [ ] **Manage data connections** — click "Manage data connections", edit a
      connection's credentials, save, and confirm no error is shown.
- [ ] **Local file ingestion through SDL** — configure a local-file pipeline,
      verify data loads successfully, and confirm new observations appear in the
      associated datastream.
- [ ] **Scheduler timing and status propagation** — verify last run, next run,
      queued/running/paused states, and pause/resume behavior stay in sync between
      SDL and HydroServer.

---

## Section 12 — HydroShare

- [ ] **Disconnected-state archival UI** — on a site details page, confirm the
      archival configuration action is absent when the account is not connected to
      HydroShare.
- [ ] **Connect / disconnect HydroShare** — connect an account through HydroShare
      OAuth, verify the linked state in the profile UI, then disconnect and verify
      the link is removed cleanly.
- [ ] **Create new HydroShare resource** — configure archival for a site, create
      a new resource, and verify metadata, public visibility, and uploaded files.
- [ ] **Archive now / update settings** — re-run archival after changing folder or
      datastream selections and verify the output is updated correctly.
- [ ] **Link to existing HydroShare resource** — connect a site to an existing
      HydroShare resource and verify archival works against the linked target.
- [ ] **Unlink HydroShare archival** — unlink the site from HydroShare and verify
      the UI returns to the unconfigured state.
