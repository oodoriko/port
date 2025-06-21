import { Card, Tabs, Text, Title } from "@mantine/core";
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
  } = results;

  // Create data points with timestamps as x-axis
  const createChartData = (curve: number[], label: string) => {
    if (
      !curve ||
      curve.length === 0 ||
      !timestamps ||
      timestamps.length === 0
    ) {
      return [];
    }
    // Use all data instead of limiting to 200 records
    return curve.map((value, index) => ({
      timestamp: timestamps[index] * 1000, // Convert to milliseconds for JS Date
      [label]: value || 0,
    }));
  };

  // Custom tooltip formatter for currency values
  const formatCurrency = (value: number) => {
    if (Math.abs(value) >= 1000000) {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        notation: "scientific",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);
    }
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  // Y-axis formatter for scientific notation
  const formatYAxis = (value: number) => {
    if (Math.abs(value) >= 100000) {
      return value.toExponential(1);
    }
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    }).format(value);
  };

  // Format timestamp for display - always include date and time for start/end display
  const formatTimestampFull = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  // Format timestamp for display - handle different time scales
  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);

    // Check if we have timestamps within the same day (small time scale)
    if (timestamps && timestamps.length > 1) {
      const firstTimestamp = timestamps[0] * 1000;
      const lastTimestamp = timestamps[timestamps.length - 1] * 1000;
      const timeDiff = lastTimestamp - firstTimestamp;

      // Less than 1 day - show time
      if (timeDiff < 24 * 60 * 60 * 1000) {
        return date.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
      }
      // Less than 7 days - show date and time
      else if (timeDiff < 7 * 24 * 60 * 60 * 1000) {
        return (
          date.toLocaleDateString([], {
            month: "short",
            day: "numeric",
          }) +
          " " +
          date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })
        );
      }
    }

    // Default to date only for longer time periods
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div
          style={{
            backgroundColor: "white",
            padding: "10px",
            border: "1px solid #ccc",
            borderRadius: "4px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          }}
        >
          <p
            style={{ margin: 0, fontWeight: "bold" }}
          >{`Date: ${formatTimestamp(label)}`}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ margin: "4px 0", color: entry.color }}>
              {`${entry.dataKey}: ${formatCurrency(entry.value)}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const tabsData = [
    {
      value: "equity",
      label: "Equity",
      data: createChartData(equity_curve, "equity"),
      color: "#2563eb",
    },
    {
      value: "cash",
      label: "Cash",
      data: createChartData(cash_curve, "cash"),
      color: "#16a34a",
    },
    {
      value: "notional",
      label: "Notional",
      data: createChartData(notional_curve, "notional"),
      color: "#dc2626",
    },
    {
      value: "pnl",
      label: "P&L",
      data: (() => {
        if (
          !realized_pnl_curve ||
          !unrealized_pnl_curve ||
          !timestamps ||
          timestamps.length === 0
        ) {
          return [];
        }

        if (
          realized_pnl_curve.length === 0 &&
          unrealized_pnl_curve.length === 0
        ) {
          return [];
        }

        const maxLength = Math.max(
          realized_pnl_curve.length,
          unrealized_pnl_curve.length
        );

        // Ensure we don't exceed timestamps length
        const actualLength = Math.min(maxLength, timestamps.length);

        const pnlData = Array.from({ length: actualLength }, (_, index) => ({
          timestamp: timestamps[index] * 1000, // Convert to milliseconds for JS Date
          realized: realized_pnl_curve[index] || 0,
          unrealized: unrealized_pnl_curve[index] || 0,
        }));

        return pnlData;
      })(),
      color: "#7c3aed",
      isMultiLine: true,
    },
    {
      value: "costs",
      label: "Cost",
      data: createChartData(cost_curve, "costs"),
      color: "#ea580c",
    },
  ];

  return (
    <Card shadow="xs" padding="md" radius="sm">
      <Title order={4} mb="md">
        Portfolio Performance Curves
      </Title>

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
            {timestamps && timestamps.length > 0 && (
              <Text size="sm" c="dimmed" mb="md">
                {`Start: ${formatTimestampFull(
                  timestamps[0] * 1000
                )} | End: ${formatTimestampFull(
                  timestamps[timestamps.length - 1] * 1000
                )}`}
              </Text>
            )}

            {tab.data.length === 0 ? (
              <div
                style={{
                  width: "100%",
                  height: "600px",
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
              <div style={{ width: "100%", height: "600px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={tab.data}
                    margin={{ top: 20, right: 30, left: 10, bottom: 50 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis
                      dataKey="timestamp"
                      type="number"
                      scale="linear"
                      domain={["dataMin", "dataMax"]}
                      tickCount={6}
                      tickFormatter={formatTimestamp}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                      {...(tab.isMultiLine && {
                        label: {
                          value: "Date",
                          position: "insideBottom",
                          offset: -10,
                        },
                      })}
                    />
                    <YAxis
                      type="number"
                      domain={
                        tab.value === "pnl"
                          ? ["dataMin - 100", "dataMax + 100"]
                          : ["auto", "auto"]
                      }
                      tickFormatter={formatYAxis}
                      allowDataOverflow={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    {tab.isMultiLine && <Legend />}

                    {tab.value === "pnl" ? (
                      <>
                        <Line
                          type="monotone"
                          dataKey="unrealized"
                          stroke="#dc2626"
                          strokeWidth={3}
                          dot={false}
                          name="Unrealized P&L"
                          isAnimationActive={false}
                          connectNulls={true}
                        />
                        <Line
                          type="monotone"
                          dataKey="realized"
                          stroke="#16a34a"
                          strokeWidth={3}
                          dot={false}
                          name="Realized P&L"
                          isAnimationActive={false}
                          connectNulls={true}
                        />
                      </>
                    ) : (
                      <Line
                        type="monotone"
                        dataKey={
                          Object.keys(tab.data[0] || {}).find(
                            (key) => key !== "timestamp"
                          ) || ""
                        }
                        stroke={tab.color}
                        strokeWidth={3}
                        dot={false}
                        name={tab.label}
                        isAnimationActive={false}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </Tabs.Panel>
        ))}
      </Tabs>
    </Card>
  );
}
