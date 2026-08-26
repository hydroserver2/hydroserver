# HydroServer Design System Conventions

Short version: don't invent values or one-off markup when this package
already has an answer. Check here first, then the organized token files,
`vuetify.ts`, `components.css`, and `vue/` for the actual definitions.

## Where things live

- `colors.css` — the canonical semantic color palette (`--hs-*`).
  `vuetify-colors.ts` is generated from it for Vuetify.
- `layout.css` — spacing, radius, and shadow tokens (`--hs-space-*`,
  `--hs-radius-*`, `--hs-shadow-*`).
- `typography.css` — font families, weights, sizes (`--hs-font-*`), and the
  `.hs-text-*` and `.hs-heading` / `.hs-subheading` / `.hs-title` /
  `.hs-label` type-recipe classes.
- `vuetify.ts` — the Vuetify adapter for the shared color roles, plus
  component defaults (button variants, text field/select/autocomplete behavior).
- `components.css` — shared recipes for recurring hand-built controls
  (search inputs, stat cards) that aren't plain Vuetify components.
- `html.css` — the shared native-HTML adapter for Django and other non-Vue pages;
  it maps native cards, fields, alerts, and button aliases to the same theme
  roles and tokens used by Vuetify.
- `vue/` — shared Vue components (`Hs*.vue`). Use one of these before
  building a bespoke layout that duplicates it.

## Color

- Never hardcode a hex value or `rgb()` literal in app code. Use a
  Vuetify theme role (`rgb(var(--v-theme-primary))`, `color="primary"`,
  utility classes like `.text-primary`) or an `--hs-*` semantic CSS token.
- Add a new color only in `colors.css` as a named semantic role — never as a
  raw value in a component, app, or Vuetify adapter. Regenerate
  `vuetify-colors.ts` after changing it.

## Spacing & radius

- Pick from `--hs-space-*` / `--hs-radius-*` in `layout.css` instead of
  writing a new px value. If nothing in the scale fits, that's a signal to reconsider
  the layout before adding a token.
- Perfect circles (avatars, status dots) stay literal `border-radius: 50%`
  — that's a shape, not a step on the radius scale.

## Typography

- Use recipes from `typography.css` (`.hs-heading`, `.hs-subheading`, `.hs-title`,
  `.hs-label`) instead of recomposing it inline every time. The goal is to
  keep to a small and set list of font recipes so the typography looks polished
  and intentional.

## Buttons

- Use the semantic button aliases — `VBtnPrimary`, `VBtnSecondary`,
  `VBtnDelete`, `VBtnCancel`, `VBtnAdd`, `VBtnIcon`, and
  `VBtnPageAction` — not bare `VBtn` with manual `color`/`variant` props.
  `VBtnIcon` is the neutral treatment for compact icon-only controls.
  `VBtnPageAction` is green and reserved for the one action that most advances
  a page or major tab's goal; use blue `VBtnPrimary` for dialog submit actions.
  Each alias already encodes the right color, shape, and emphasis for its role.

## Forms

- Text fields, selects, autocompletes, textareas, and checkboxes inherit
  shared defaults (`variant: 'outlined'`, autofill disabled on
  menu-based inputs) from `vuetify.ts` — don't override these per
  instance unless the field is genuinely special-cased.
- Mark required fields with the `.required-label` class, not a manual
  asterisk + color.
- For server-rendered pages, use the native-control classes in `html.css`
  (`.hs-form`, `.hs-field`, `.hs-button`, `.hs-alert`) instead of creating
  app-local form-control recipes.

## Shared components over bespoke markup

- Before building a new empty state, nav rail, detail panel, stat
  card, or search input, check `vue/` and `components.css` — there is
  likely an `Hs*` component or `.hs-*` recipe already covering it.
- Extend a shared component/recipe when the need is close but not
  exact, rather than forking a parallel implementation in one app.

## Adding to the system

- A new token/role/recipe belongs in this package only if it's shared
  across apps (or clearly will be soon). App-specific one-offs stay in
  the app.
