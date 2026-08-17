/**
 * HydroServer's primitive color palette.
 *
 * These are physical colors, not UI roles. Semantic names such as `surface`,
 * `primary`, and `onSurface` belong in theme mappings, where each theme can
 * assign stable roles to these primitives.
 *
 * Keep this list deliberately small: add a color only when it is intended to
 * be available across every HydroServer application.
 */
export const colors = {
  neutral: {
    0: 'oklch(100% 0 0)',
    25: 'oklch(99.39% 0.0029 264.54)',
    50: 'oklch(97.47% 0.0051 247.88)',
    100: 'oklch(96.18% 0.0086 247.91)',
    300: 'oklch(87.76% 0.0176 248.03)',
    700: 'oklch(46.9% 0.0313 251.93)',
    950: 'oklch(26.4% 0.0274 251.05)',
  },
  blue: {
    600: 'oklch(49.59% 0.1051 252.95)',
  },
  green: {
    500: 'oklch(68.37% 0.1364 141.36)',
  },
} as const

export type HydroServerColors = typeof colors

/**
 * sRGB hexadecimal equivalents of the OKLCH palette above.
 *
 * Prefer `colors` in CSS-capable consumers. This parallel export exists for
 * integrations such as Vuetify whose color parser does not yet accept OKLCH.
 * Keep both objects in the same order so their correspondence stays obvious.
 */
export const hexColors = {
  neutral: {
    0: '#FFFFFF',
    25: '#FCFDFF',
    50: '#F4F7FA',
    100: '#EEF3F8',
    300: '#CED8E2',
    700: '#4E5C6C',
    950: '#1B2632',
  },
  blue: {
    600: '#32649C',
  },
  green: {
    500: '#66AE5C',
  },
} as const

export type HydroServerHexColors = typeof hexColors
