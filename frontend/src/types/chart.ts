import type { UTCTimestamp } from "lightweight-charts";

export interface OHLCVData {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartData {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface VolumeData {
  time: UTCTimestamp;
  value: number;
  color?: string;
}

export type Ticker = "BTC-USD" | "ETH-USD" | "SOL-USD" | "ADA-USD" | "DOT-USD";
