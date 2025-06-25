import {
  Accordion,
  Badge,
  Box,
  Divider,
  Fieldset,
  Grid,
  Group,
  NumberFormatter,
  Stack,
  Text,
} from "@mantine/core";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { MANTINE_THEME_A_COLORS, THEME_A_COLORS } from "../theme/theme_a";
import type { BacktestResult } from "../types/backtest";

interface BacktestResultsProps {
  results: BacktestResult;
}

// Use only non-black/white colors, fallback to a known blue if needed
const PIE_COLORS = [
  THEME_A_COLORS.primary.blue || "#2774AE",
  "#FF6B6B",
  "#4ECDC4",
  "#45B7D1",
  "#96CEB4",
  "#FFEAA7",
  "#DDA0DD",
  "#98D8C8",
];

export function BacktestResults({ results }: BacktestResultsProps) {
  const { backtest_id, portfolio_name, key_metrics, tickers } = results;

  // Prepare pie chart data
  const pieData = tickers.map((ticker, i) => ({
    name: ticker,
    value: key_metrics.composition[i],
    percent: key_metrics.composition[i],
    markValue: key_metrics.composition[i] * key_metrics.market_value,
  }));
  const isLiquidated = pieData.every((d) => d.value === 0);
  const allClosed =
    key_metrics.position_metrics.length > 0 &&
    key_metrics.position_metrics.every((pm) => pm.status === "Closed");
  const showComposition = !isLiquidated && !allClosed;

  return (
    <Stack gap="md">
      <Fieldset
        legend={
          <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
            Overview
          </Text>
        }
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            <Text component="span" fw={500}>
              Backtest ID:
            </Text>{" "}
            {backtest_id}
          </Text>

          <Grid>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Portfolio Name
              </Text>
              <Text size="lg" fw={600}>
                {portfolio_name}
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                # of Trades
              </Text>
              <Text size="lg" fw={600}>
                {key_metrics.num_trades}
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Duration
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.duration}
                  suffix=" yrs"
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Status
              </Text>
              <Text size="lg" fw={600}>
                {key_metrics.status}
              </Text>
            </Grid.Col>
          </Grid>
        </Stack>
      </Fieldset>

      <Fieldset
        legend={
          <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
            Portfolio Performance
          </Text>
        }
      >
        <Stack gap="md">
          {/* First row: Market Value and Peak Equity */}
          <Grid>
            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Market Value
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.market_value}
                  prefix="$"
                  thousandSeparator
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Peak Equity
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.peak_equity}
                  prefix="$"
                  thousandSeparator
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
          </Grid>

          {/* Second row: Cash Injection and Net Realized PnL */}
          <Grid>
            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Cash Injection
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.cash_injection}
                  prefix="$"
                  thousandSeparator
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Net Realized PnL
              </Text>
              <Text
                size="lg"
                fw={600}
                c={
                  !Number.isFinite(key_metrics.net_realized_pnl)
                    ? "black"
                    : key_metrics.net_realized_pnl === 0
                    ? "black"
                    : key_metrics.net_realized_pnl >= 0
                    ? "green"
                    : "red"
                }
              >
                {Number.isFinite(key_metrics.net_realized_pnl) ? (
                  <NumberFormatter
                    value={key_metrics.net_realized_pnl}
                    prefix="$"
                    thousandSeparator
                    decimalScale={2}
                  />
                ) : (
                  <span style={{ color: "black" }}>-</span>
                )}
              </Text>
            </Grid.Col>
          </Grid>

          {/* Third row: Pie Chart for Composition, only if not liquidated and not all closed */}
          {showComposition && (
            <Grid align="center" gutter={0}>
              {/* Left: Mark values */}
              <Grid.Col span={6}>
                <Stack gap={4} style={{ minWidth: 120 }}>
                  {pieData.map((entry, i) => (
                    <Group key={entry.name} gap={6} align="center">
                      <Box
                        w={10}
                        h={10}
                        style={{
                          backgroundColor:
                            i === 0
                              ? THEME_A_COLORS.primary.blue
                              : i === 1
                              ? THEME_A_COLORS.primary.gold
                              : i === 2
                              ? THEME_A_COLORS.system.teal
                              : i === 3
                              ? THEME_A_COLORS.system.pink
                              : i === 4
                              ? THEME_A_COLORS.system.orange
                              : THEME_A_COLORS.system.lightBlue,
                          borderRadius: 2,
                        }}
                      />
                      <Text size="xs" fw={500}>
                        {entry.name}
                      </Text>
                      <Text
                        size="xs"
                        fw={700}
                        style={{
                          color:
                            i === 0
                              ? THEME_A_COLORS.primary.blue
                              : i === 1
                              ? THEME_A_COLORS.primary.gold
                              : i === 2
                              ? THEME_A_COLORS.system.teal
                              : i === 3
                              ? THEME_A_COLORS.system.pink
                              : i === 4
                              ? THEME_A_COLORS.system.orange
                              : THEME_A_COLORS.system.lightBlue,
                        }}
                      >
                        <NumberFormatter
                          value={entry.markValue}
                          prefix="$"
                          thousandSeparator
                          decimalScale={2}
                        />
                      </Text>
                      <Text size="xs" c="dimmed">
                        {(entry.percent * 100).toFixed(1)}%
                      </Text>
                    </Group>
                  ))}
                </Stack>
              </Grid.Col>
              {/* Right: Pie chart */}
              <Grid.Col span={6}>
                <Box style={{ minWidth: 100, width: 100, height: 100 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={45}
                        innerRadius={25}
                        paddingAngle={2}
                        isAnimationActive={false}
                      >
                        {pieData.map((entry, i) => (
                          <Cell
                            key={`cell-${i}`}
                            fill={
                              i === 0
                                ? THEME_A_COLORS.primary.blue
                                : i === 1
                                ? THEME_A_COLORS.primary.gold
                                : i === 2
                                ? THEME_A_COLORS.system.teal
                                : i === 3
                                ? THEME_A_COLORS.system.pink
                                : i === 4
                                ? THEME_A_COLORS.system.orange
                                : THEME_A_COLORS.system.lightBlue
                            }
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(
                          value: number,
                          name: string,
                          props: any
                        ) => [`${(value * 100).toFixed(1)}%`, name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Grid.Col>
            </Grid>
          )}

          {/* Divider with Return Metrics label */}
          <Divider
            label={
              <Text fw={600} size="sm">
                Return Metrics
              </Text>
            }
            labelPosition="center"
            my="sm"
          />

          {/* Compact 3-column layout for returns and win/profit metrics */}
          <Grid>
            {/* Column 1: Gross Return, Win Rate */}
            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Gross Return
              </Text>
              <Text
                size="lg"
                fw={600}
                c={
                  !Number.isFinite(key_metrics.gross_return)
                    ? "black"
                    : key_metrics.gross_return === 0
                    ? "black"
                    : key_metrics.gross_return >= 0
                    ? "green"
                    : "red"
                }
              >
                {Number.isFinite(key_metrics.gross_return) ? (
                  <NumberFormatter
                    value={key_metrics.gross_return * 100}
                    suffix="%"
                    decimalScale={2}
                  />
                ) : (
                  <span style={{ color: "black" }}>-</span>
                )}
              </Text>
              <Text size="sm" c="dimmed" mt="md" mb="xs">
                Win Rate
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.win_rate * 100}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            {/* Column 2: Net Return, Profit Factor */}
            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Net Return
              </Text>
              <Text
                size="lg"
                fw={600}
                c={
                  !Number.isFinite(key_metrics.net_return)
                    ? "black"
                    : key_metrics.net_return === 0
                    ? "black"
                    : key_metrics.net_return >= 0
                    ? "green"
                    : "red"
                }
              >
                {Number.isFinite(key_metrics.net_return) ? (
                  <NumberFormatter
                    value={key_metrics.net_return * 100}
                    suffix="%"
                    decimalScale={2}
                  />
                ) : (
                  <span style={{ color: "black" }}>-</span>
                )}
              </Text>
              <Text size="sm" c="dimmed" mt="md" mb="xs">
                Profit Factor
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.profit_factor}
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            {/* Column 3: Annualized Return (spans both rows) */}
            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Annualized Return
              </Text>
              <Text
                size="lg"
                fw={600}
                c={
                  !Number.isFinite(key_metrics.annualized_return)
                    ? "black"
                    : key_metrics.annualized_return === 0
                    ? "black"
                    : key_metrics.annualized_return >= 0
                    ? "green"
                    : "red"
                }
              >
                {Number.isFinite(key_metrics.annualized_return) ? (
                  <NumberFormatter
                    value={key_metrics.annualized_return * 100}
                    suffix="%"
                    decimalScale={2}
                  />
                ) : (
                  <span style={{ color: "black" }}>-</span>
                )}
              </Text>
            </Grid.Col>
          </Grid>

          {/* Divider with Risk Metrics label */}
          <Divider
            label={
              <Text fw={600} size="sm">
                Risk Metrics (rf: {key_metrics.risk_free_rate})
              </Text>
            }
            labelPosition="center"
            style={{ flex: 1 }}
          />

          {/* Risk metrics row: Sharpe, Sortino, Calmar, Max Drawdown */}
          <Grid>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Sharpe Ratio
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.sharpe_ratio}
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Sortino Ratio
              </Text>
              <Text size="lg" fw={600}>
                <NumberFormatter
                  value={key_metrics.sortino_ratio}
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Calmar Ratio
              </Text>
              <Text size="lg" fw={600}>
                {Number.isFinite(key_metrics.calmar_ratio) ? (
                  <NumberFormatter
                    value={key_metrics.calmar_ratio}
                    decimalScale={2}
                  />
                ) : (
                  <span style={{ color: "black" }}>-</span>
                )}
              </Text>
            </Grid.Col>
            <Grid.Col span={3}>
              <Text size="sm" c="dimmed" mb="xs">
                Max Drawdown
              </Text>
              <Text size="lg" fw={600} c="red">
                <NumberFormatter
                  value={key_metrics.max_drawdown * 100}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
          </Grid>
        </Stack>
      </Fieldset>

      {/* Position Performance Box */}
      <Fieldset
        legend={
          <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
            Position Performance
          </Text>
        }
      >
        <Stack gap="md">
          <Accordion variant="contained">
            {key_metrics.position_metrics.map((position, idx) => (
              <Accordion.Item key={idx} value={`position-${idx}`}>
                <Accordion.Control>
                  <Group gap="md" justify="space-between">
                    <Group gap="md">
                      <Text fw={500}>{tickers[position.asset_name]}</Text>
                      <Badge
                        color={position.status === "Open" ? "green" : "gray"}
                        variant="light"
                        size="sm"
                      >
                        {position.status}
                      </Badge>
                    </Group>
                    <Badge color="blue" variant="light" size="sm">
                      {position.num_trades.toFixed(0)} trades
                    </Badge>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Grid mb="md">
                    {/* Column 1 */}
                    <Grid.Col span={3}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Realized PnL
                      </Text>
                      <Text
                        size="lg"
                        fw={600}
                        c={
                          !Number.isFinite(position.realized_pnl_net)
                            ? "black"
                            : position.realized_pnl_net === 0
                            ? "black"
                            : position.realized_pnl_net >= 0
                            ? "green"
                            : "red"
                        }
                      >
                        {Number.isFinite(position.realized_pnl_net) ? (
                          <NumberFormatter
                            value={position.realized_pnl_net}
                            prefix="$"
                            thousandSeparator
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                      <Text size="sm" c="dimmed" mt="md" mb="xs">
                        Gross Return
                      </Text>
                      <Text
                        size="lg"
                        fw={600}
                        c={
                          !Number.isFinite(position.gross_return)
                            ? "black"
                            : position.gross_return === 0
                            ? "black"
                            : position.gross_return >= 0
                            ? "green"
                            : "red"
                        }
                      >
                        {Number.isFinite(position.gross_return) ? (
                          <NumberFormatter
                            value={position.gross_return * 100}
                            suffix="%"
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                      <Text size="sm" c="dimmed" mt="md" mb="xs">
                        Win Rate
                      </Text>
                      <Text size="lg" fw={600}>
                        {Number.isFinite(position.win_rate) ? (
                          <NumberFormatter
                            value={position.win_rate * 100}
                            suffix="%"
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                    </Grid.Col>
                    {/* Column 2 */}
                    <Grid.Col span={3}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Unrealized PnL
                      </Text>
                      <Text
                        size="lg"
                        fw={600}
                        c={
                          !Number.isFinite(position.unrealized_pnl_net)
                            ? "black"
                            : position.unrealized_pnl_net === 0
                            ? "black"
                            : position.unrealized_pnl_net >= 0
                            ? "green"
                            : "red"
                        }
                      >
                        {Number.isFinite(position.unrealized_pnl_net) ? (
                          <NumberFormatter
                            value={position.unrealized_pnl_net}
                            prefix="$"
                            thousandSeparator
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                      <Text size="sm" c="dimmed" mt="md" mb="xs">
                        Net Return
                      </Text>
                      <Text
                        size="lg"
                        fw={600}
                        c={
                          !Number.isFinite(position.net_return)
                            ? "black"
                            : position.net_return === 0
                            ? "black"
                            : position.net_return >= 0
                            ? "green"
                            : "red"
                        }
                      >
                        {Number.isFinite(position.net_return) ? (
                          <NumberFormatter
                            value={position.net_return * 100}
                            suffix="%"
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                      <Text size="sm" c="dimmed" mt="md" mb="xs">
                        Profit Factor
                      </Text>
                      <Text size="lg" fw={600}>
                        {Number.isFinite(position.profit_factor) ? (
                          <NumberFormatter
                            value={position.profit_factor}
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                    </Grid.Col>
                    {/* Column 3 */}
                    <Grid.Col span={3}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Alpha
                      </Text>
                      <Text size="lg" fw={600}>
                        N/A
                      </Text>
                      <Text size="sm" c="dimmed" mt="md" mb="xs">
                        Ann. Return
                      </Text>
                      <Text
                        size="lg"
                        fw={600}
                        c={
                          !Number.isFinite(position.annualized_return)
                            ? "black"
                            : position.annualized_return === 0
                            ? "black"
                            : position.annualized_return >= 0
                            ? "green"
                            : "red"
                        }
                      >
                        {Number.isFinite(position.annualized_return) ? (
                          <NumberFormatter
                            value={position.annualized_return * 100}
                            suffix="%"
                            decimalScale={2}
                          />
                        ) : (
                          <span style={{ color: "black" }}>-</span>
                        )}
                      </Text>
                    </Grid.Col>
                    {/* Column 4 */}
                    <Grid.Col span={3}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Beta
                      </Text>
                      <Text size="lg" fw={600}>
                        N/A
                      </Text>
                    </Grid.Col>
                  </Grid>

                  {/* Trade Statistics Table */}
                  <Box mt="lg">
                    <Text size="sm" c="dimmed" mb="xs">
                      Trade Type Breakdown
                    </Text>
                    <Grid>
                      {/* Left: Trade Statistics Table (2/3 width) */}
                      <Grid.Col span={8}>
                        <Box
                          style={{
                            border: `1px solid ${THEME_A_COLORS.system.gray}`,
                            borderRadius: 8,
                            overflow: "hidden",
                          }}
                        >
                          {/* Table Header */}
                          <Grid
                            style={{
                              borderBottom: `1px solid ${THEME_A_COLORS.system.gray}`,
                            }}
                            m={0}
                          >
                            <Grid.Col span={3} p="xs">
                              <Text size="xs" fw={600} c="dimmed">
                                Type
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="xs" fw={600} c="dimmed">
                                Trades %
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="xs" fw={600} c="dimmed">
                                Gain %
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="xs" fw={600} c="dimmed">
                                Loss %
                              </Text>
                            </Grid.Col>
                          </Grid>

                          {/* Table Rows */}
                          {/* Take Profit Row */}
                          <Grid
                            m={0}
                            style={{
                              borderBottom: `1px solid ${THEME_A_COLORS.system.warmGray3}`,
                            }}
                          >
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" fw={500}>
                                Take Profit
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm">
                                {Number.isFinite(
                                  position.take_profit_trades_pct
                                ) ? (
                                  <NumberFormatter
                                    value={
                                      position.take_profit_trades_pct * 100
                                    }
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="green">
                                {Number.isFinite(
                                  position.take_profit_gain_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.take_profit_gain_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="red">
                                {Number.isFinite(
                                  position.take_profit_loss_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.take_profit_loss_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                          </Grid>

                          {/* Stop Loss Row */}
                          <Grid
                            m={0}
                            style={{
                              borderBottom: `1px solid ${THEME_A_COLORS.system.warmGray3}`,
                            }}
                          >
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" fw={500}>
                                Stop Loss
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm">
                                {Number.isFinite(
                                  position.stop_loss_trades_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.stop_loss_trades_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="green">
                                {Number.isFinite(
                                  position.stop_loss_gain_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.stop_loss_gain_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="red">
                                {Number.isFinite(
                                  position.stop_loss_loss_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.stop_loss_loss_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                          </Grid>

                          {/* Signal Sell Row */}
                          <Grid m={0}>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" fw={500}>
                                Signal Sell
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm">
                                {Number.isFinite(
                                  position.signal_sell_trades_pct
                                ) ? (
                                  <NumberFormatter
                                    value={
                                      position.signal_sell_trades_pct * 100
                                    }
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="green">
                                {Number.isFinite(
                                  position.signal_sell_gain_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.signal_sell_gain_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                            <Grid.Col span={3} p="xs">
                              <Text size="sm" c="red">
                                {Number.isFinite(
                                  position.signal_sell_loss_pct
                                ) ? (
                                  <NumberFormatter
                                    value={position.signal_sell_loss_pct * 100}
                                    suffix="%"
                                    decimalScale={1}
                                  />
                                ) : (
                                  <span style={{ color: "black" }}>-</span>
                                )}
                              </Text>
                            </Grid.Col>
                          </Grid>
                        </Box>
                      </Grid.Col>

                      {/* Right: Buy/Sell Pie Chart (1/3 width) */}
                      <Grid.Col span={4}>
                        <Box>
                          <Box style={{ minWidth: 80, width: 80, height: 80 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie
                                  data={[
                                    {
                                      name: "Buy",
                                      value: position.buy_pct,
                                      percent: position.buy_pct,
                                    },
                                    {
                                      name: "Sell",
                                      value: position.sell_pct,
                                      percent: position.sell_pct,
                                    },
                                  ]}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={35}
                                  innerRadius={20}
                                  paddingAngle={2}
                                  isAnimationActive={false}
                                >
                                  <Cell fill={THEME_A_COLORS.primary.blue} />
                                  <Cell fill={THEME_A_COLORS.primary.gold} />
                                </Pie>
                                <Tooltip
                                  formatter={(value: number, name: string) => [
                                    `${(value * 100).toFixed(1)}%`,
                                    name,
                                  ]}
                                />
                              </PieChart>
                            </ResponsiveContainer>
                          </Box>

                          {/* Legend */}
                          <Stack gap={4} mt="md">
                            <Group gap={6} align="center">
                              <Box
                                w={8}
                                h={8}
                                style={{
                                  backgroundColor: THEME_A_COLORS.primary.blue,
                                  borderRadius: 2,
                                }}
                              />
                              <Text size="xs" fw={500}>
                                Buy
                              </Text>
                              <Text
                                size="xs"
                                fw={700}
                                style={{ color: THEME_A_COLORS.primary.blue }}
                              >
                                {(position.buy_pct * 100).toFixed(1)}%
                              </Text>
                            </Group>
                            <Group gap={6} align="center">
                              <Box
                                w={8}
                                h={8}
                                style={{
                                  backgroundColor: THEME_A_COLORS.primary.gold,
                                  borderRadius: 2,
                                }}
                              />
                              <Text size="xs" fw={500}>
                                Sell
                              </Text>
                              <Text
                                size="xs"
                                fw={700}
                                style={{ color: THEME_A_COLORS.primary.gold }}
                              >
                                {(position.sell_pct * 100).toFixed(1)}%
                              </Text>
                            </Group>
                          </Stack>
                        </Box>
                      </Grid.Col>
                    </Grid>
                  </Box>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Stack>
      </Fieldset>
    </Stack>
  );
}
