// Theme C University Official Brand Colors
// Based on official brand guidelines

export const THEME_C_COLORS = {
  // Core Colors (Primary palette since 1920s)
  core: {
    primaryRed: "#C41230",
    black: "#000000",
    ironGray: "#6D6E71",
    steelGray: "#E0E0E0",
    white: "#FFFFFF",
  },

  // Secondary Colors - Tartan Palette (Bold, Youthful, Passionate, Fearless, Audacious)
  tartan: {
    scotsRose: "#EF3A47",
    goldThread: "#FDB515",
    greenThread: "#009647",
    tealThread: "#008F91",
    blueThread: "#043673",
    highlandsSkyBlue: "#007BC0",
  },

  // Secondary Colors - Campus Palette (Insightful, Conscientious, Creative, Pragmatic, Entrepreneurial)
  campus: {
    machineryHallTan: "#BCB49E",
    kittanningBrickBeige: "#E4DAC4",
    hornbostelTeal: "#1F4C4C",
    palladianGreen: "#719F94",
    weaverBlue: "#182C4B",
    skiboRed: "#941120",
  },
} as const;

// Semantic color assignments for the trading application
export const TRADING_COLORS_C = {
  buy: THEME_C_COLORS.tartan.goldThread, // Gold Thread - energetic, positive action
  risk: THEME_C_COLORS.tartan.blueThread, // Blue Thread - trustworthy, stable
  sell: THEME_C_COLORS.tartan.greenThread, // Green Thread - action, success
  primary: THEME_C_COLORS.core.primaryRed, // Primary Red - primary brand color
  secondary: THEME_C_COLORS.core.ironGray, // Iron Gray - supporting color
  accent: THEME_C_COLORS.tartan.tealThread, // Teal Thread - accent color
} as const;

// Mantine-compatible color names (for c prop usage)
export const MANTINE_THEME_C_COLORS = {
  // Map colors to closest Mantine color names for easy usage
  primaryRed: "red.7",
  goldThread: "yellow.6",
  blueThread: "blue.9",
  greenThread: "green.7",
  tealThread: "teal.7",
  ironGray: "gray.7",
  steelGray: "gray.3",
} as const;

export type ThemeCColorKey = keyof typeof MANTINE_THEME_C_COLORS;
