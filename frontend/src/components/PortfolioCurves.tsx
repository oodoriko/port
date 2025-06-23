import { Alert, Card, Tabs, Text, Title } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestResult } from "../types/backtest";

interface PortfolioCurvesProps {
  results: BacktestResult;
}

export function PortfolioCurves({ results }: PortfolioCurvesProps) {
  const {
    equity_curve,
    cash_curve,
    notional_curve,
    cost_curve,
    realized_pnl_curve,
    unrealized_pnl_curve,
    timestamps,
    trade_timestamps,
  } = results;

  // Helper function to calculate cumulative sum
  const calculateCumulative = (values: number[]): number[] => {
    let cumSum = 0;
    return values.map((value) => {
      cumSum += value;
      return cumSum;
    });
  };

  // Create data points with full timestamps
  const createChartData = (
    curve: number[],
    label: string,
    isCumulative = false
  ) => {
    if (
      !curve ||
      curve.length === 0 ||
      !timestamps ||
      timestamps.length === 0
    ) {
      return [];
    }

    const actualLength = Math.min(curve.length, timestamps.length);
    const processedCurve = isCumulative
      ? calculateCumulative(curve.slice(0, actualLength))
      : curve.slice(0, actualLength);

    return Array.from({ length: actualLength }, (_, index) => ({
      timestamp: timestamps[index] * 1000,
      [label]: processedCurve[index] || 0,
      isTradeDay: trade_timestamps.includes(timestamps[index]),
    }));
  };

  // Create filtered data that only shows points on trade days
  const createTradeFilteredData = (
    curve: number[],
    label: string,
    isCumulative = false
  ) => {
    if (
      !curve ||
      curve.length === 0 ||
      !timestamps ||
      timestamps.length === 0 ||
      !trade_timestamps ||
      trade_timestamps.length === 0
    ) {
      return [];
    }

    const tradeTimestampSet = new Set(trade_timestamps);
    const actualLength = Math.min(curve.length, timestamps.length);
    const processedCurve = isCumulative
      ? calculateCumulative(curve.slice(0, actualLength))
      : curve.slice(0, actualLength);

    return Array.from({ length: actualLength }, (_, index) => ({
      timestamp: timestamps[index] * 1000,
      [label]: processedCurve[index] || 0,
      isTradeDay: tradeTimestampSet.has(timestamps[index]),
    })).filter((point) => point.isTradeDay);
  };

  // Custom tooltip formatter
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  // Y-axis formatter
  const formatYAxis = (value: number) => {
    if (Math.abs(value) >= 1000000) {
      return (value / 1000000).toFixed(1) + "M";
    } else if (Math.abs(value) >= 1000) {
      return (value / 1000).toFixed(1) + "K";
    }
    return value.toFixed(0);
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: "2-digit",
    });
  };

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const date = new Date(label);
      return (
        <div
          style={{
            backgroundColor: "white",
            padding: "12px",
            border: "1px solid #ccc",
            borderRadius: "6px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
        >
          <p style={{ margin: 0, fontWeight: "bold", marginBottom: "8px" }}>
            {date.toLocaleDateString()} {date.toLocaleTimeString()}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ margin: "4px 0", color: entry.color }}>
              <span style={{ fontWeight: "500" }}>
                {entry.name || entry.dataKey}:
              </span>{" "}
              {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Combined P&L data with both realized and unrealized
  const createPnLData = (showTradeOnly = false) => {
    if (
      !realized_pnl_curve ||
      !unrealized_pnl_curve ||
      !timestamps ||
      timestamps.length === 0
    ) {
      return [];
    }

    if (realized_pnl_curve.length === 0 && unrealized_pnl_curve.length === 0) {
      return [];
    }

    const actualLength = Math.min(
      Math.min(realized_pnl_curve.length, unrealized_pnl_curve.length),
      timestamps.length
    );

    const cumulativeRealized = calculateCumulative(
      realized_pnl_curve.slice(0, actualLength)
    );
    const tradeTimestampSet = new Set(trade_timestamps || []);

    const allData = Array.from({ length: actualLength }, (_, index) => ({
      timestamp: timestamps[index] * 1000,
      realized: cumulativeRealized[index] || 0,
      unrealized: unrealized_pnl_curve[index] || 0,
      total:
        (cumulativeRealized[index] || 0) + (unrealized_pnl_curve[index] || 0),
      isTradeDay: tradeTimestampSet.has(timestamps[index]),
    }));

    const filteredData = showTradeOnly
      ? allData.filter((point) => point.isTradeDay)
      : allData;

    return filteredData;
  };

  const tabsData = [
    {
      value: "equity",
      label: "Equity",
      fullData: createChartData(equity_curve, "equity"),
      tradeData: createTradeFilteredData(equity_curve, "equity"),
      color: "#2563eb",
      description: "Portfolio total value over time",
    },
    {
      value: "cash",
      label: "Cash",
      fullData: createChartData(cash_curve, "cash"),
      tradeData: createTradeFilteredData(cash_curve, "cash"),
      color: "#16a34a",
      description: "Available cash balance over time",
    },
    {
      value: "notional",
      label: "Notional",
      fullData: createChartData(notional_curve, "notional"),
      tradeData: createTradeFilteredData(notional_curve, "notional"),
      color: "#dc2626",
      description: "Total position values over time",
    },
    {
      value: "costs",
      label: "Cumulative Cost",
      fullData: createChartData(cost_curve, "costs", true),
      tradeData: createTradeFilteredData(cost_curve, "costs", true),
      color: "#ea580c",
      description: "Cumulative trading costs over time",
    },
    {
      value: "pnl",
      label: "P&L Analysis",
      fullData: createPnLData(false),
      tradeData: createPnLData(true),
      color: "#7c3aed",
      isMultiLine: true,
      description: "Realized and unrealized profit & loss over time",
    },
  ];

  return (
    <Card shadow="xs" padding="md" radius="sm">
      <Title order={4} mb="md">
        Portfolio Performance Curves
      </Title>

      <Alert icon={<IconInfoCircle size={16} />} mb="md" variant="light">
        Charts show both complete time series and trade-day filtered views. P&L
        shows cumulative realized gains/losses and current unrealized positions.
      </Alert>

      <Tabs defaultValue="equity" variant="outline">
        <Tabs.List grow>
          {tabsData.map((tab) => (
            <Tabs.Tab key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>

        {tabsData.map((tab) => (
          <Tabs.Panel key={tab.value} value={tab.value} pt="md">
            <div>
              <Text size="sm" c="dimmed" mb="md">
                {tab.description}
              </Text>

              {/* Trade Summary */}
              {trade_timestamps && trade_timestamps.length > 0 && (
                <Text size="xs" c="blue" mb="md">
                  {`${trade_timestamps.length} trading days out of ${
                    timestamps?.length || 0
                  } total periods`}
                </Text>
              )}

              {/* Full Time Series Chart */}
              <div style={{ marginBottom: "32px" }}>
                <Text size="sm" fw={500} mb="xs">
                  Complete Time Series
                </Text>
                {tab.fullData.length === 0 ? (
                  <div
                    style={{
                      width: "100%",
                      height: "400px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: "#f8f9fa",
                      borderRadius: "8px",
                      border: "1px solid #e9ecef",
                    }}
                  >
                    <Text c="dimmed" size="sm">
                      No data available for this chart
                    </Text>
                  </div>
                ) : (
                  <div style={{ width: "100%", height: "400px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={tab.fullData}
                        margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          dataKey="timestamp"
                          type="number"
                          scale="time"
                          domain={["dataMin", "dataMax"]}
                          tickCount={6}
                          tickFormatter={formatTimestamp}
                        />
                        <YAxis tickFormatter={formatYAxis} />
                        <Tooltip content={<CustomTooltip />} />
                        {tab.isMultiLine && <Legend />}

                        {tab.value === "pnl" ? (
                          <>
                            <Line
                              type="monotone"
                              dataKey="realized"
                              stroke="#16a34a"
                              strokeWidth={2}
                              dot={false}
                              name="Cumulative Realized P&L"
                              isAnimationActive={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="unrealized"
                              stroke="#dc2626"
                              strokeWidth={2}
                              dot={false}
                              name="Unrealized P&L"
                              isAnimationActive={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="total"
                              stroke="#7c3aed"
                              strokeWidth={3}
                              dot={false}
                              name="Total P&L"
                              isAnimationActive={false}
                              strokeDasharray="5 5"
                            />
                          </>
                        ) : (
                          <Line
                            type="monotone"
                            dataKey={
                              Object.keys(tab.fullData[0] || {}).find(
                                (key) =>
                                  key !== "timestamp" && key !== "isTradeDay"
                              ) || ""
                            }
                            stroke={tab.color}
                            strokeWidth={2}
                            dot={false}
                            name={tab.label}
                            isAnimationActive={false}
                          />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Trade-Filtered Chart */}
              <div>
                <Text size="sm" fw={500} mb="xs">
                  Trade Days Only ({tab.tradeData.length} points)
                </Text>
                {tab.tradeData.length === 0 ? (
                  <div
                    style={{
                      width: "100%",
                      height: "300px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: "#f8f9fa",
                      borderRadius: "8px",
                      border: "1px solid #e9ecef",
                    }}
                  >
                    <Text c="dimmed" size="sm">
                      No trade data available
                    </Text>
                  </div>
                ) : (
                  <div style={{ width: "100%", height: "300px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={tab.tradeData}
                        margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          dataKey="timestamp"
                          type="number"
                          scale="time"
                          domain={["dataMin", "dataMax"]}
                          tickCount={4}
                          tickFormatter={formatTimestamp}
                        />
                        <YAxis tickFormatter={formatYAxis} />
                        <Tooltip content={<CustomTooltip />} />
                        {tab.isMultiLine && <Legend />}

                        {tab.value === "pnl" ? (
                          <>
                            <Line
                              type="monotone"
                              dataKey="realized"
                              stroke="#16a34a"
                              strokeWidth={3}
                              dot={{ r: 4 }}
                              name="Cumulative Realized P&L"
                              isAnimationActive={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="unrealized"
                              stroke="#dc2626"
                              strokeWidth={3}
                              dot={{ r: 4 }}
                              name="Unrealized P&L"
                              isAnimationActive={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="total"
                              stroke="#7c3aed"
                              strokeWidth={4}
                              dot={{ r: 5 }}
                              name="Total P&L"
                              isAnimationActive={false}
                              strokeDasharray="5 5"
                            />
                          </>
                        ) : (
                          <Line
                            type="monotone"
                            dataKey={
                              Object.keys(tab.tradeData[0] || {}).find(
                                (key) =>
                                  key !== "timestamp" && key !== "isTradeDay"
                              ) || ""
                            }
                            stroke={tab.color}
                            strokeWidth={3}
                            dot={{ r: 4 }}
                            name={tab.label}
                            isAnimationActive={false}
                          />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Card>
  );
}
