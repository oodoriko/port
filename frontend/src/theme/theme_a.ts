// Theme A University Official Brand Colors
// Based on official brand guidelines

export const THEME_A_COLORS = {
  // Primary Colors
  primary: {
    blue: "#2774AE",
    gold: "#FFD100",
    white: "#FFFFFF",
    black: "#000000",
  },

  // Secondary Colors - Blue Tones
  blues: {
    darkestBlue: "#003B5C",
    darkerBlue: "#005587",
    lighterBlue: "#8BB8E8",
    lightestBlue: "#C3D7EE",
  },

  // Secondary Colors - Gold Tones
  golds: {
    darkestGold: "#FFB81C",
    darkerGold: "#FFC72C",
  },

  // Tertiary Colors (Vibrant Palette)
  tertiary: {
    yellow: "#FFFF00",
    green: "#00FF87",
    magenta: "#FF00A5",
    cyan: "#00FFFF",
    purple: "#8237FF",
  },

  // UC System Colors (Extended palette)
  system: {
    ucBlue: "#1295D8",
    ucGold: "#FFB511",
    lightBlue: "#72CDF4",
    lightGold: "#FFE552",
    teal: "#00778B",
    lightTeal: "#00A3AD",
    pink: "#E44C9A",
    lightPink: "#FEB2E0",
    orange: "#FF6E1B",
    lightOrange: "#FF8F28",
    darkBlue: "#002033",
    extraLightBlue: "#BDE3F6",
    darkGray: "#171717",
    gray: "#4C4C4C",
    ucGray: "#7C7E7F",
    warmGray8: "#8F8884",
    warmGray3: "#BEB6AF",
    warmGray1: "#DBD5CD",
  },
} as const;

// Semantic color assignments for the trading application
export const TRADING_COLORS_A = {
  buy: THEME_A_COLORS.golds.darkestGold, // Darkest Gold - wealth, prosperity
  risk: THEME_A_COLORS.primary.blue, // Primary Blue - trust, stability
  sell: THEME_A_COLORS.tertiary.green, // Green - success, go
  primary: THEME_A_COLORS.primary.blue, // Primary Blue - main brand
  secondary: THEME_A_COLORS.blues.darkerBlue, // Darker Blue - supporting
  accent: THEME_A_COLORS.system.teal, // Teal - accent color
} as const;

// Mantine-compatible color names (for c prop usage)
export const MANTINE_THEME_A_COLORS = {
  // Map colors to closest Mantine color names for easy usage
  primaryBlue: "blue.6",
  primaryGold: "yellow.4",
  darkestBlue: "blue.9",
  darkerBlue: "blue.8",
  lighterBlue: "blue.3",
  darkestGold: "yellow.6",
  darkerGold: "yellow.5",
  teal: "teal.6",
  green: "green.5",
  purple: "violet.6",
} as const;

export type ThemeAColorKey = keyof typeof MANTINE_THEME_A_COLORS;
