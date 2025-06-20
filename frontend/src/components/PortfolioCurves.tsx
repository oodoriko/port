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
  } = results;

  // Create data points with index as x-axis (time periods)
  const createChartData = (curve: number[], label: string) => {
    // Limit to first 200 periods for better visualization
    const limitedCurve = curve.slice(0, 200);
    return limitedCurve.map((value, index) => ({
      period: index,
      [label]: value,
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
          <p style={{ margin: 0, fontWeight: "bold" }}>{`Period: ${label}`}</p>
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
      label: "Portfolio Equity",
      data: createChartData(equity_curve, "equity"),
      color: "#2563eb",
      description: "Total portfolio value over time",
    },
    {
      value: "cash",
      label: "Cash Position",
      data: createChartData(cash_curve, "cash"),
      color: "#16a34a",
      description: "Available cash in the portfolio",
    },
    {
      value: "notional",
      label: "Notional Value",
      data: createChartData(notional_curve, "notional"),
      color: "#dc2626",
      description: "Market value of all positions",
    },
    {
      value: "pnl",
      label: "P&L Analysis",
      data: realized_pnl_curve.slice(0, 200).map((realized, index) => ({
        period: index,
        realized: realized,
        unrealized: unrealized_pnl_curve[index] || 0,
      })),
      color: "#7c3aed",
      description: "Realized vs Unrealized profit and loss",
      isMultiLine: true,
    },
    {
      value: "costs",
      label: "Cumulative Costs",
      data: createChartData(cost_curve, "costs"),
      color: "#ea580c",
      description: "Trading costs and fees over time",
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
            <Text size="sm" c="dimmed" mb="md">
              {tab.description}
            </Text>

            <div style={{ width: "100%", height: "400px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={tab.data}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="period"
                    label={{
                      value: "Time Period",
                      position: "insideBottom",
                      offset: -5,
                    }}
                    domain={[0, 200]}
                    type="number"
                    tickCount={6}
                  />
                  <YAxis
                    tickFormatter={formatYAxis}
                    label={{
                      value: "Value ($)",
                      angle: -90,
                      position: "insideLeft",
                    }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />

                  {tab.isMultiLine ? (
                    <>
                      <Line
                        type="monotone"
                        dataKey="realized"
                        stroke="#16a34a"
                        strokeWidth={2}
                        dot={false}
                        name="Realized P&L"
                      />
                      <Line
                        type="monotone"
                        dataKey="unrealized"
                        stroke="#dc2626"
                        strokeWidth={2}
                        dot={false}
                        name="Unrealized P&L"
                      />
                    </>
                  ) : (
                    <Line
                      type="monotone"
                      dataKey={
                        Object.keys(tab.data[0] || {}).find(
                          (key) => key !== "period"
                        ) || ""
                      }
                      stroke={tab.color}
                      strokeWidth={2}
                      dot={false}
                      name={tab.label}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Card>
  );
}
