const API_BASE_URL = "http://localhost:8080";

export interface TradingPairsResponse {
  pairs: string[];
}

export interface DateRangesResponse {
  date_ranges: Record<string, [number, number]>;
}

export async function fetchTradingPairs(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/trading-pairs`);
  if (!response.ok) {
    throw new Error(`Failed to fetch trading pairs: ${response.statusText}`);
  }
  const data: TradingPairsResponse = await response.json();
  return data.pairs;
}

export async function fetchDateRanges(): Promise<
  Record<string, [number, number]>
> {
  const response = await fetch(`${API_BASE_URL}/api/date-ranges`);
  if (!response.ok) {
    throw new Error(`Failed to fetch date ranges: ${response.statusText}`);
  }
  const data: DateRangesResponse = await response.json();
  return data.date_ranges;
}
