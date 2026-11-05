# Reservoir profile stakeholder demo (#632)

Normal `npm run dev` / `npm run docker-dev` now adds four public profile fixture
streams alongside the live visualization data. Open Visualize Data and filter by
**Datastream type → Profile**. The synthetic site is at
<http://127.0.0.1:1203/sites/profile-demo>. The streams are Dissolved oxygen, Temperature,
Chlorophyll-a, and Specific conductance, each with seasonal visits and depth values.
No fixture records are written to your database. Set `VITE_PROFILE_FIXTURES=0` to
hide them during development. A normal production build excludes this overlay.

For a standalone demo without a backend, run from `apps/data-management`:

```sh
npm run dev:profiles
```

Open <http://127.0.0.1:1203/visualize-data?datastreams=profile-oxygen>.
On the [fixture Site Details page](http://127.0.0.1:1203/sites/profile-demo),
each blue SVG preview opens the same viewer in a popup. The popup's visualization link preserves the
comparison. This runs without Django, a database, or a login. All data is synthetic.

Try selecting historical visits, switching to Compare analytes, adding Temperature,
removing it to choose a different analyte, and changing the visit. Chlorophyll-a is
unavailable at the latest visit; an older visit makes it available. The July 31 visit
has a missing measurement, which leaves a gap in the curve. Depth increases downward.
Only one primary profile can be plotted; selecting Water level switches back to the
existing time series view. Clear the selection to use the Datastream type filter
(Time Series, Profile, Discrete), or use `type:Profile` in the search field.
CSV downloads include the vertical coordinate.

## Fixture boundary and backend handoff

Normal development serves fixture HTTP endpoints under `/__fixtures/profiles`.
`src/services/profileFixtureTransport.ts` routes only the reserved synthetic IDs
to those local endpoints and appends the fixture bootstrap to the live bootstrap.
Real datastream reads and writes retain their original requests. The synthetic site
and metadata also resolve locally, including when the SDK calls Django directly.

`VITE_PROFILE_FIXTURES=1` enables standalone mode in `profileFixtures.ts` for
development (or preview of a build made with the same flag). This mode supplies
the entire read-only demo API. Fixture endpoints reject writes.
The plugin also supplies read-only site, metadata, bootstrap, time series observation,
and CSV responses so the real app pages can be demonstrated without backend support.
No backend or generated client contracts are modified.

`src/services/profiles.ts` is the temporary adapter for:

```
GET /api/ogc/collections/datastreams/items/{id}/profiles
```

It currently returns `ProfileData` (`src/models/profile.ts`):

- `zReference`, `zUnit`, `positiveDirection` (down or up).
- `visits`: exact `phenomenonTime`, display label, and demo status.
- `analytes`: datastream ID, name, unit. These are compatible datastreams at the site.
- `observations`: datastream ID, phenomenon time, `z`, and nullable numeric `result`.

The endpoint and visit/status representation are provisional, not an agreed backend
contract. They can be replaced in this adapter with the eventual observation
row/column queries. Follow Ken's #630 proposal: `type: profileCoverage`, vertical
reference/unit metadata, and an observation `z` coordinate; do not use
`observationType` for the frontend distinction. App types temporarily extend the
current SDK without editing generated files. Analytes compare only at a shared
visit, with separate value axes and one optional companion. Missing results are
kept as gaps. Shared visit matching currently uses the exact phenomenon timestamp.

Profile comparison state is included in the visualization URL (`profileMode`,
`profileVisits`, `profileVisit`, `profileAnalyte`). The regular filters/layout state
continues to use the existing URL parameters.
