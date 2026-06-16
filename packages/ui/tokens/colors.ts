export const colorShades = [
  50, 100, 200, 300, 400, 500, 600, 700, 800, 900,
] as const;

export type ColorShade = (typeof colorShades)[number];

export const colors = {
  blue: {
    50: "oklch(0.953 0.022 239.43)", // Material Blue 50, #E3F2FD
    100: "oklch(0.885 0.055 243.39)", // #BBDEFB
    200: "oklch(0.816 0.09 243.62)", // #90CAF9
    300: "oklch(0.748 0.123 244.75)", // #64B5F6
    400: "oklch(0.7 0.149 246.66)", // #42A5F5
    500: "oklch(0.658 0.169 248.81)", // #2196F3
    600: "oklch(0.618 0.167 250.87)", // #1E88E5
    700: "oklch(0.565 0.163 253.27)", // #1976D2
    800: "oklch(0.513 0.16 255.67)", // #1565C0
    900: "oklch(0.422 0.157 259.91)", // #0D47A1
  },
  green: {
    50: "oklch(0.957 0.021 147.64)", // Material Green 50, #E8F5E9
    100: "oklch(0.895 0.05 146.04)", // #C8E6C9
    200: "oklch(0.829 0.083 145.82)", // #A5D6A7
    300: "oklch(0.766 0.118 145.3)", // #81C784
    400: "oklch(0.718 0.142 144.89)", // #66BB6A
    500: "oklch(0.673 0.162 144.21)", // #4CAF50
    600: "oklch(0.629 0.154 144.2)", // #43A047
    700: "oklch(0.575 0.145 144.18)", // #388E3C
    800: "oklch(0.523 0.135 144.17)", // #2E7D32
    900: "oklch(0.425 0.116 144.31)", // #1B5E20
  },
  lightBlue: {
    50: "oklch(0.958 0.024 226.47)", // Material Light Blue 50, #E1F5FE
    100: "oklch(0.895 0.06 227.77)", // #B3E5FC
    200: "oklch(0.831 0.097 229.09)", // #81D4FA
    300: "oklch(0.773 0.127 231.11)", // #4FC3F7
    400: "oklch(0.734 0.145 234.62)", // #29B6F6
    500: "oklch(0.699 0.157 238.99)", // #03A9F4
    600: "oklch(0.659 0.152 240.75)", // #039BE5
    700: "oklch(0.603 0.147 243.46)", // #0288D1
    800: "oklch(0.551 0.139 245.43)", // #0277BD
    900: "oklch(0.452 0.131 251.01)", // #01579B
  },
  teal: {
    50: "oklch(0.948 0.019 192.81)", // Material Teal 50, #E0F2F1
    100: "oklch(0.871 0.047 189.63)", // #B2DFDB
    200: "oklch(0.791 0.075 188.24)", // #80CBC4
    300: "oklch(0.712 0.098 186.68)", // #4DB6AC
    400: "oklch(0.656 0.107 185.34)", // #26A69A
    500: "oklch(0.605 0.107 183.38)", // #009688
    600: "oklch(0.566 0.101 182.45)", // #00897B
    700: "oklch(0.517 0.093 181.08)", // #00796B
    800: "oklch(0.467 0.084 180.4)", // #00695C
    900: "oklch(0.376 0.07 176.4)", // #004D40
  },
  purple: {
    50: "oklch(0.938 0.026 321.94)", // Material Purple 50, #F3E5F5
    100: "oklch(0.844 0.068 321.36)", // #E1BEE7
    200: "oklch(0.744 0.116 321.55)", // #CE93D8
    300: "oklch(0.645 0.162 321.61)", // #BA68C8
    400: "oklch(0.576 0.194 321.59)", // #AB47BC
    500: "oklch(0.517 0.215 321.24)", // #9C27B0
    600: "oklch(0.49 0.208 317.97)", // #8E24AA
    700: "oklch(0.453 0.199 312.96)", // #7B1FA2
    800: "oklch(0.42 0.19 308.04)", // #6A1B9A
    900: "oklch(0.36 0.176 296.26)", // #4A148C
  },
  indigo: {
    50: "oklch(0.939 0.016 278.5)", // Material Indigo 50, #E8EAF6
    100: "oklch(0.845 0.043 278.18)", // #C5CAE9
    200: "oklch(0.742 0.073 276.54)", // #9FA8DA
    300: "oklch(0.638 0.105 274.91)", // #7986CB
    400: "oklch(0.556 0.132 273.79)", // #5C6BC0
    500: "oklch(0.478 0.159 271.4)", // #3F51B5
    600: "oklch(0.451 0.157 271.6)", // #3949AB
    700: "oklch(0.416 0.156 271.17)", // #303F9F
    800: "oklch(0.382 0.154 271)", // #283593
    900: "oklch(0.321 0.151 270.29)", // #1A237E
  },
  cyan: {
    50: "oklch(0.96 0.024 206.2)", // Material Cyan 50, #E0F7FA
    100: "oklch(0.903 0.059 205.57)", // #B2EBF2
    200: "oklch(0.847 0.091 206.2)", // #80DEEA
    300: "oklch(0.793 0.114 207.31)", // #4DD0E1
    400: "oklch(0.759 0.124 208.28)", // #26C6DA
    500: "oklch(0.729 0.126 210.82)", // #00BCD4
    600: "oklch(0.682 0.118 210.05)", // #00ACC1
    700: "oklch(0.619 0.106 207.97)", // #0097A7
    800: "oklch(0.557 0.095 206.08)", // #00838F
    900: "oklch(0.444 0.076 199.77)", // #006064
  },
  amber: {
    50: "oklch(0.979 0.031 92.94)", // Material Amber 50, #FFF8E1
    100: "oklch(0.945 0.076 91.82)", // #FFECB3
    200: "oklch(0.913 0.119 91.67)", // #FFE082
    300: "oklch(0.886 0.154 91.23)", // #FFD54F
    400: "oklch(0.862 0.168 88.31)", // #FFCA28
    500: "oklch(0.844 0.172 84.93)", // #FFC107
    600: "oklch(0.818 0.171 77.95)", // #FFB300
    700: "oklch(0.784 0.172 68.09)", // #FFA000
    800: "oklch(0.755 0.178 59.69)", // #FF8F00
    900: "oklch(0.708 0.197 46.46)", // #FF6F00
  },
  orange: {
    50: "oklch(0.969 0.028 79.48)", // Material Orange 50, #FFF3E0
    100: "oklch(0.921 0.069 77.49)", // #FFE0B2
    200: "oklch(0.874 0.11 76.47)", // #FFCC80
    300: "oklch(0.829 0.145 73.54)", // #FFB74D
    400: "oklch(0.797 0.164 69.62)", // #FFA726
    500: "oklch(0.77 0.174 64.05)", // #FF9800
    600: "oklch(0.745 0.176 59.37)", // #FB8C00
    700: "oklch(0.712 0.179 53.54)", // #F57C00
    800: "oklch(0.68 0.185 48.15)", // #EF6C00
    900: "oklch(0.631 0.197 40.25)", // #E65100
  },
  red: {
    50: "oklch(0.957 0.022 7.17)", // Material Red 50, #FFEBEE
    100: "oklch(0.893 0.057 11.54)", // #FFCDD2
    200: "oklch(0.772 0.102 19.67)", // #EF9A9A
    300: "oklch(0.688 0.142 21.46)", // #E57373
    400: "oklch(0.654 0.193 25.14)", // #EF5350
    500: "oklch(0.643 0.215 28.81)", // #F44336
    600: "oklch(0.608 0.209 27.03)", // #E53935
    700: "oklch(0.568 0.2 26.41)", // #D32F2F
    800: "oklch(0.539 0.194 26.72)", // #C62828
    900: "oklch(0.502 0.189 27.48)", // #B71C1C
  },
  grey: {
    50: "oklch(0.985 0 0)", // Material Grey 50, #FAFAFA
    100: "oklch(0.97 0 0)", // #F5F5F5
    200: "oklch(0.949 0 0)", // #EEEEEE
    300: "oklch(0.907 0 0)", // #E0E0E0
    400: "oklch(0.798 0 0)", // #BDBDBD
    500: "oklch(0.699 0 0)", // #9E9E9E
    600: "oklch(0.562 0 0)", // #757575
    700: "oklch(0.493 0 0)", // #616161
    800: "oklch(0.379 0 0)", // #424242
    900: "oklch(0.248 0 0)", // #212121
  },
  blueGrey: {
    50: "oklch(0.95 0.004 236.5)", // Material Blue Grey 50, #ECEFF1
    100: "oklch(0.877 0.011 226)", // #CFD8DC
    200: "oklch(0.793 0.018 229.07)", // #B0BEC5
    300: "oklch(0.706 0.027 229.31)", // #90A4AE
    400: "oklch(0.639 0.033 229.55)", // #78909C
    500: "oklch(0.572 0.04 229.02)", // #607D8B
    600: "oklch(0.522 0.036 227.88)", // #546E7A
    700: "oklch(0.454 0.03 228.62)", // #455A64
    800: "oklch(0.387 0.025 229.79)", // #37474F
    900: "oklch(0.309 0.019 229.78)", // #263238
  },
  pink: {
    50: "oklch(0.941 0.028 355.44)", // Material Pink 50, #FCE4EC
    100: "oklch(0.853 0.075 356.33)", // #F8BBD0
    200: "oklch(0.766 0.128 358.96)", // #F48FB1
    300: "oklch(0.688 0.18 1.96)", // #F06292
    400: "oklch(0.639 0.21 5.28)", // #EC407A
    500: "oklch(0.606 0.23 9.63)", // #E91E63
    600: "oklch(0.574 0.218 7.85)", // #D81B60
    700: "oklch(0.531 0.202 5.62)", // #C2185B
    800: "oklch(0.49 0.187 2.53)", // #AD1457
    900: "oklch(0.415 0.16 355.69)", // #880E4F
  },
  lime: {
    50: "oklch(0.981 0.026 111.51)", // Material Lime 50, #F9FBE7
    100: "oklch(0.952 0.064 111.39)", // #F0F4C3
    200: "oklch(0.924 0.104 112.98)", // #E6EE9C
    300: "oklch(0.896 0.139 113.76)", // #DCE775
    400: "oklch(0.874 0.16 114.29)", // #D4E157
    500: "oklch(0.856 0.177 114.85)", // #CDDC39
    600: "oklch(0.805 0.165 113.4)", // #C0CA33
    700: "oklch(0.742 0.151 111.71)", // #AFB42B
    800: "oklch(0.676 0.135 109.04)", // #9E9D24
    900: "oklch(0.562 0.11 102.38)", // #827717
  },
  brown: {
    50: "oklch(0.943 0.005 48.68)", // Material Brown 50, #EFEBE9
    100: "oklch(0.853 0.013 41.19)", // #D7CCC8
    200: "oklch(0.752 0.023 39.35)", // #BCAAA4
    300: "oklch(0.647 0.033 40.8)", // #A1887F
    400: "oklch(0.566 0.043 40.43)", // #8D6E63
    500: "oklch(0.485 0.053 40.69)", // #795548
    600: "oklch(0.45 0.049 39.21)", // #6D4C41
    700: "oklch(0.402 0.044 37.96)", // #5D4037
    800: "oklch(0.354 0.039 33.47)", // #4E342E
    900: "oklch(0.3 0.036 30.2)", // #3E2723
  },
} as const;

export const baseColors = {
  white: "oklch(1 0 0)",
  black: "oklch(0 0 0)",
  navbar: "oklch(0.301 0.029 265.2)", // #272E3D
  darkBackground: "oklch(0.243 0.022 248.73)", // #18212A
  textPrimary: "oklch(0.248 0.006 271.18)", // #202124
  textSecondary: "oklch(0.498 0.009 253.91)", // #5F6368
} as const;

export const semanticColors = {
  brand: colors.blue[500],
  brandSubtle: colors.blue[50],
  brandStrong: colors.blue[800],
  secondary: colors.green[500],
  secondarySubtle: colors.green[50],
  secondaryStrong: colors.green[800],
  background: colors.grey[50],
  surface: baseColors.white,
  border: colors.grey[200],
  text: {
    primary: baseColors.textPrimary,
    secondary: baseColors.textSecondary,
    inverse: baseColors.white,
  },
  state: {
    info: colors.lightBlue[500],
    success: colors.green[500],
    warning: colors.orange[500],
    error: colors.red[500],
    delete: colors.red[500],
    pending: colors.blue[800],
    paused: colors.blueGrey[600],
    unknown: colors.grey[600],
  },
} as const;

export const orchestrationColors = {
  ingestion: {
    accent: colors.blue[800],
    accentLight: colors.blue[50],
  },
  dataProducts: {
    accent: colors.purple[800],
    accentDark: colors.purple[900],
    accentLight: colors.purple[50],
  },
  quality: {
    accent: colors.teal[800],
    accentLight: colors.teal[50],
  },
  workspace: {
    accent: colors.green[800],
    accentLight: colors.green[50],
  },
  status: {
    ok: colors.green[800],
    needsAttention: colors.red[900],
    behindSchedule: colors.orange[900],
    loadingPaused: colors.blueGrey[600],
    pending: colors.blue[800],
    empty: "oklch(0.829 0.018 308.22)", // #CAC4D0
  },
  dataProductType: {
    aggregation: {
      text: colors.purple[800],
      background: colors.purple[50],
    },
    expression: {
      text: colors.cyan[900],
      background: colors.cyan[50],
    },
    derivation: {
      text: colors.amber[800],
      background: colors.amber[50],
    },
    ratingCurve: {
      text: colors.indigo[800],
      background: colors.indigo[50],
    },
  },
} as const;

export const pageColors = {
  browse: colors.lightBlue[700],
  sites: colors.green[700],
  metadata: colors.purple[700],
  visualizeData: colors.cyan[700],
  orchestration: colors.blue[800],
  workspaces: colors.green[800],
  hydroShare: colors.teal[700],
  account: colors.blueGrey[700],
  settings: colors.grey[700],
} as const;
