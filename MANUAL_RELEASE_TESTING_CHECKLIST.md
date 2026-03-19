# HydroServer Manual Release Testing Checklist

This document is for release checks that are still outside the deterministic CI
gate. If a workflow can be exercised reliably in local fixtures or in
Playwright, it should move out of this checklist and into automation.

Work through this list before production release alongside CI.

---

## Section 2 — Browse / Map Page

- [ ] **Workspace filter** — filter the Browse page by workspace and confirm the
      site list updates to the selected workspace only.
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

- [ ] **Initiate a workspace transfer** — as the current owner, submit a transfer
      to the destination user and confirm the UI warns about the ownership change
      and reports that the transfer is pending.
- [ ] **Accept a workspace transfer** — log in as the destination user, open the
      pending transfer dialog, click "Accept transfer", and confirm the workspace
      now appears in the destination user's workspace list and is removed from the
      source user's list.
- [ ] **Cancel a workspace transfer** — log in as the destination user, open the
      pending transfer dialog, click "Cancel transfer", and confirm the workspace
      remains with the source user.
- [ ] **Pending-transfer permissions** — while the transfer is pending, confirm
      the destination user can see the workspace sites but cannot edit them.
- [ ] **Completed-transfer ownership state** — after acceptance, confirm the new
      owner is shown as the owner in the workspace UI, can edit sites in the
      workspace, and the original owner no longer owns the workspace.

---

## Section 6 — Your Sites / Workspace Maps

- [ ] **Map extent / zoom behavior** — open `Your Sites`, switch between
      workspaces, and verify the map zooms to the extent of the visible sites.
- [ ] **Site metadata filter drawer** — apply a key/value metadata filter and
      confirm the site list narrows correctly; clear the filter and confirm the
      full list returns.
- [ ] **Registered sites search** — use the Your Sites search box and confirm the
      visible sites filter correctly.
- [ ] **Collaborator access verification** — after adding or changing a
      collaborator role, log in as that collaborator and confirm the resulting
      access matches the assigned role.
- [ ] **Register a new site** — create a site from the Your Sites page and confirm
      the site appears with the saved metadata.
- [ ] **Register a site with key/value metadata** — create or edit a site with
      key/value metadata and confirm those values appear correctly on the site
      details page.
- [ ] **Site photo drag-and-drop** — create or edit a site using drag-and-drop
      photo upload and confirm the image is persisted and visible on the site
      details page.

---

## Section 7 — Site Details / Datastreams

- [ ] **Site-details map interaction** — interact with the map on the site
      details page and confirm marker/location behavior remains correct.
- [ ] **Site privacy visibility** — toggle a site to private and confirm it is no
      longer visible on Browse for users without access; restore the original
      visibility after the check.
- [ ] **Load Template button** — on the "Add datastream" form, click "Load
      Template", select an existing orchestration template, and confirm the form
      pre-fills with the template's field values.
- [ ] **Datastream form auto-fill controls** — verify any auto-fill controls on
      the datastream form populate fields with the expected values.
- [ ] **Datastream privacy visibility** — toggle datastream privacy and confirm
      users without access can no longer see the datastream metadata.
- [ ] **Datastream data visibility** — toggle data visibility and confirm users
      without access can no longer retrieve the data while the datastream record
      still behaves as expected for authorized users.
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
- [ ] **Site-to-visualization deep link** — from a sparkline popup or datastream
      action, open the visualization page and confirm the selected datastream and
      time range carry over.
- [ ] **Site-details datastream metadata modal** — open a datastream metadata
      panel from the site details page and confirm the sections expand correctly
      and CSV download works.

---

## Section 8 — Visualize Data

- [ ] **Left-side filters** — exercise the visualization filters and confirm the
      datastream table updates to match the selected filters.
- [ ] **Multi-series plot correctness** — select multiple datastreams and verify
      each series renders with a distinct color/axis and that the axes auto-scale
      sensibly.
- [ ] **Plot brush / zoom** — drag on the Plotly chart to zoom into a time range.
      Confirm the axes update. Click "Reset zoom" and confirm the axes return to
      the full range.
- [ ] **Summary statistics correctness** — enable summary mode for one and
      multiple datastreams and confirm the values update when the selected date
      range changes.
- [ ] **Datastream search** — use the table search box and confirm the table
      filters to matching datastreams.
- [ ] **Download selected datastreams** — verify selected download behavior for
      both a single datastream and multiple datastreams.
- [ ] **Metadata modal clear-and-plot** — from a datastream metadata modal, use
      the clear-and-plot path and confirm the plot resets to the selected
      datastream only.
- [ ] **Plot PNG export** — download the plot image and confirm a valid PNG is
      produced for the currently displayed chart state.
- [ ] **Show / hide columns** — toggle the column visibility control (if present)
      and verify that selected columns appear and disappear from the datastream
      table.

---

## Section 9 — Metadata

- [ ] **System metadata visibility** — verify system-level metadata appears where
      expected and is distinct from workspace metadata.
- [ ] **Deletion guard for in-use metadata** — attempt to delete metadata that is
      attached to an existing datastream and confirm the UI blocks the deletion.

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

- [ ] **Workspace selection** — change the selected workspace and confirm the
      visible orchestration systems update accordingly.
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
