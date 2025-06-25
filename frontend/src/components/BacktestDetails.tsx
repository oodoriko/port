import {
  Box,
  Button,
  Collapse,
  Divider,
  Fieldset,
  Grid,
  Group,
  NumberFormatter,
  Stack,
  Text,
} from "@mantine/core";
import { useState } from "react";
import { MANTINE_THEME_A_COLORS, THEME_A_COLORS } from "../theme/theme_a";
import { THEME_C_COLORS } from "../theme/theme_c";
import type { BacktestParams, BacktestResult } from "../types/backtest";
import { LineChart } from "./LineChart";

interface BacktestDetailsProps {
  backtestParams: BacktestParams;
  backtestResult?: BacktestResult;
}

export function BacktestDetails({
  backtestParams,
  backtestResult,
}: BacktestDetailsProps) {
  const [opened, setOpened] = useState(false);
  const [performanceOpened, setPerformanceOpened] = useState(false);
  const [signalSummaryOpened, setSignalSummaryOpened] = useState(false);
  const [curvesOpened, setCurvesOpened] = useState(false);
  const {
    portfolio_params,
    portfolio_constraints_params,
    position_constraints_params,
    strategies,
    tickers,
  } = backtestParams;
  backtestResult?.timestamps.sort((a, b) => a - b);
  return (
    <Stack gap="md">
      {/* Signal Summary */}
      <Fieldset
        legend={
          <Group gap="xs" justify="space-between" style={{ width: "100%" }}>
            <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
              Signal Summary
            </Text>
            <Button
              variant="subtle"
              size="xs"
              onClick={() => setSignalSummaryOpened(!signalSummaryOpened)}
              style={{
                padding: "2px 6px",
                height: "auto",
                fontSize: "12px",
                minWidth: "auto",
                color: MANTINE_THEME_A_COLORS.teal,
                marginLeft: "auto",
              }}
            >
              {signalSummaryOpened ? "Hide" : "Show"}
            </Button>
          </Group>
        }
      >
        <Collapse in={signalSummaryOpened}>
          <Stack gap="md">
            {/* Executed Trades */}
            <Divider
              label={
                <Text fw={600} size="sm">
                  Executed Trades
                </Text>
              }
              labelPosition="left"
            />
            <Text size="lg" fw={600} c="green">
              {backtestResult?.trade_type_count?.executed || 0}
            </Text>

            {/* Failed Trades */}
            <Divider
              label={
                <Text fw={600} size="sm">
                  Trades Failed During Trading
                </Text>
              }
              labelPosition="left"
            />
            <Grid>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Insufficient cash after cost
                </Text>
                <Text size="lg" fw={600} c="red">
                  {backtestResult?.trade_type_count?.failed_insufficient_cash ||
                    0}
                </Text>
              </Grid.Col>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Short sell prohibited
                </Text>
                <Text size="lg" fw={600} c="red">
                  {backtestResult?.trade_type_count
                    ?.failed_short_sell_prohibited || 0}
                </Text>
              </Grid.Col>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Asset in cool down period
                </Text>
                <Text size="lg" fw={600} c="red">
                  {backtestResult?.trade_type_count?.failed_cool_down_period ||
                    0}
                </Text>
              </Grid.Col>
            </Grid>

            {/* Rejected Trades */}
            <Divider
              label={
                <Text fw={600} size="sm">
                  Trades Rejected by Constraints
                </Text>
              }
              labelPosition="left"
            />
            <Grid>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Holding period too short
                </Text>
                <Text size="lg" fw={600} c="orange">
                  {backtestResult?.trade_type_count
                    ?.rejected_holding_period_too_short || 0}
                </Text>
              </Grid.Col>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Exited at loss last time, in cool down period
                </Text>
                <Text size="lg" fw={600} c="orange">
                  {backtestResult?.trade_type_count
                    ?.rejected_cool_down_after_loss || 0}
                </Text>
              </Grid.Col>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Trade size too small
                </Text>
                <Text size="lg" fw={600} c="orange">
                  {backtestResult?.trade_type_count
                    ?.rejected_trade_size_too_small || 0}
                </Text>
              </Grid.Col>
              <Grid.Col span={3}>
                <Text size="sm" c="dimmed" mb="xs">
                  Short sell prohibited
                </Text>
                <Text size="lg" fw={600} c="orange">
                  {backtestResult?.trade_type_count
                    ?.rejected_short_sell_prohibited || 0}
                </Text>
              </Grid.Col>
            </Grid>
          </Stack>
        </Collapse>
      </Fieldset>

      <Fieldset
        legend={
          <Group gap="xs" justify="space-between" style={{ width: "100%" }}>
            <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
              Portfolio Configuration
            </Text>
            <Button
              variant="subtle"
              size="xs"
              onClick={() => setOpened(!opened)}
              style={{
                padding: "2px 6px",
                height: "auto",
                fontSize: "12px",
                minWidth: "auto",
                color: MANTINE_THEME_A_COLORS.teal,
                marginLeft: "auto",
              }}
            >
              {opened ? "Hide" : "Show"}
            </Button>
          </Group>
        }
      >
        <Collapse in={opened}>
          <Stack gap="md">
            {/* Portfolio Parameters */}
            <Box>
              <Text size="sm" c="dimmed" mb="xs" fw={500}>
                Portfolio Parameters
              </Text>
              <Text size="sm">
                <Text component="span" fw={500}>
                  Initial Cash:
                </Text>{" "}
                <NumberFormatter
                  value={portfolio_params.initial_cash}
                  prefix="$"
                  thousandSeparator
                  decimalScale={2}
                />
                {" | "}
                <Text component="span" fw={500}>
                  Capital Growth:
                </Text>{" "}
                <NumberFormatter
                  value={portfolio_params.capital_growth_pct * 100}
                  suffix="%"
                  decimalScale={2}
                />
                {" | "}
                <Text component="span" fw={500}>
                  Growth Amount:
                </Text>{" "}
                <NumberFormatter
                  value={portfolio_params.capital_growth_amount}
                  prefix="$"
                  thousandSeparator
                  decimalScale={2}
                />
                {" | "}
                <Text component="span" fw={500}>
                  Frequency:
                </Text>{" "}
                {portfolio_params.capital_growth_frequency}
              </Text>
            </Box>

            <Divider />

            {/* Portfolio Constraints */}
            <Box>
              <Text size="sm" c="dimmed" mb="xs" fw={500}>
                Portfolio Constraints
              </Text>
              <Text size="sm">
                <Text component="span" fw={500}>
                  Rebalance Threshold:
                </Text>{" "}
                <NumberFormatter
                  value={
                    portfolio_constraints_params.rebalance_threshold_pct * 100
                  }
                  suffix="%"
                  decimalScale={2}
                />
                {" | "}
                <Text component="span" fw={500}>
                  Min Cash:
                </Text>{" "}
                <NumberFormatter
                  value={portfolio_constraints_params.min_cash_pct * 100}
                  suffix="%"
                  decimalScale={2}
                />
                {" | "}
                <Text component="span" fw={500}>
                  Max Drawdown:
                </Text>{" "}
                <NumberFormatter
                  value={portfolio_constraints_params.max_drawdown_pct * 100}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Box>

            <Divider />

            {/* Positions */}
            <Box>
              <Text size="sm" c="dimmed" mb="xs" fw={500}>
                Positions
              </Text>
              <Stack gap="md">
                {position_constraints_params.map((constraints, index) => (
                  <Box key={index}>
                    <Text
                      size="sm"
                      fw={600}
                      mb="xs"
                      style={{
                        color:
                          index === 0
                            ? THEME_A_COLORS.primary.blue
                            : index === 1
                            ? THEME_A_COLORS.primary.gold
                            : index === 2
                            ? THEME_A_COLORS.system.teal
                            : index === 3
                            ? THEME_A_COLORS.system.pink
                            : index === 4
                            ? THEME_A_COLORS.system.orange
                            : THEME_A_COLORS.system.lightBlue,
                      }}
                    >
                      {tickers[index] || `Position ${index + 1}`}
                    </Text>

                    {/* Position Constraints */}
                    <Text size="sm" mb="xs">
                      <Text component="span" fw={500}>
                        Max Position:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.max_position_size_pct * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Min Trade:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.min_trade_size_pct * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Min Holding:
                      </Text>{" "}
                      {constraints.min_holding_candle}
                      {" | "}
                      <Text component="span" fw={500}>
                        Trailing Stop:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.trailing_stop_loss_pct * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Stop Update Threshold:
                      </Text>{" "}
                      <NumberFormatter
                        value={
                          constraints.trailing_stop_update_threshold_pct * 100
                        }
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                    <Text size="sm" mb="md">
                      <Text component="span" fw={500}>
                        Take Profit:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.take_profit_pct * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Risk Per Trade:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.risk_per_trade_pct * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Sell Fraction:
                      </Text>{" "}
                      <NumberFormatter
                        value={constraints.sell_fraction}
                        decimalScale={2}
                      />
                      {" | "}
                      <Text component="span" fw={500}>
                        Cool Down:
                      </Text>{" "}
                      {constraints.cool_down_period}
                    </Text>

                    {/* Strategies for this position */}
                    {strategies[index] && (
                      <Box>
                        <Stack gap="xs">
                          {strategies[index].map((strategy, strategyIndex) => (
                            <Box key={strategyIndex}>
                              {Object.entries(strategy).map(
                                ([strategyType, params]) => (
                                  <Box key={strategyType}>
                                    <Text size="sm" fw={600} mb="xs" c="dimmed">
                                      {strategyType
                                        .replace(/([A-Z])/g, " $1")
                                        .trim()}
                                    </Text>
                                    <Text size="sm" mb="xs">
                                      {Object.entries(params)
                                        .filter(
                                          ([paramName]) =>
                                            paramName.toLowerCase() !== "name"
                                        )
                                        .map(
                                          (
                                            [paramName, paramValue],
                                            paramIndex
                                          ) => (
                                            <span key={paramName}>
                                              <Text component="span" fw={500}>
                                                {paramName
                                                  .replace(/_/g, " ")
                                                  .replace(/\b\w/g, (l) =>
                                                    l.toUpperCase()
                                                  )}
                                              </Text>{" "}
                                              {typeof paramValue ===
                                              "number" ? (
                                                <NumberFormatter
                                                  value={paramValue}
                                                  decimalScale={
                                                    paramValue % 1 === 0 ? 0 : 4
                                                  }
                                                />
                                              ) : (
                                                paramValue?.toString() || "-"
                                              )}
                                              {paramIndex <
                                              Object.entries(params).filter(
                                                ([p]) =>
                                                  p.toLowerCase() !== "name"
                                              ).length -
                                                1
                                                ? " | "
                                                : ""}
                                            </span>
                                          )
                                        )}
                                    </Text>
                                  </Box>
                                )
                              )}
                            </Box>
                          ))}
                        </Stack>
                      </Box>
                    )}
                  </Box>
                ))}
              </Stack>
            </Box>
          </Stack>
        </Collapse>
      </Fieldset>

      {/* Portfolio Key Performance */}
      {backtestResult && (
        <Fieldset
          legend={
            <Group gap="xs" justify="space-between" style={{ width: "100%" }}>
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                Portfolio Key Performance
              </Text>
              <Button
                variant="subtle"
                size="xs"
                onClick={() => setPerformanceOpened(!performanceOpened)}
                style={{
                  padding: "2px 6px",
                  height: "auto",
                  fontSize: "12px",
                  minWidth: "auto",
                  color: MANTINE_THEME_A_COLORS.teal,
                  marginLeft: "auto",
                }}
              >
                {performanceOpened ? "Hide" : "Show"}
              </Button>
            </Group>
          }
        >
          <Collapse in={performanceOpened}>
            <Stack gap="md">
              {/* Overview */}
              <Box>
                <Group gap="md" align="center" mb="xs">
                  <Text size="sm" c="dimmed" fw={500}>
                    Overview
                  </Text>
                  <Text size="sm" c="dimmed">
                    ID: {backtestResult.backtest_id}
                  </Text>
                </Group>
                <Grid>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Portfolio
                    </Text>
                    <Text size="lg" fw={600}>
                      {backtestResult.portfolio_name}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      # of Trades
                    </Text>
                    <Text size="lg" fw={600}>
                      {backtestResult.key_metrics.num_trades}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Duration
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.duration}
                        suffix=" yrs"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Status
                    </Text>
                    <Text size="lg" fw={600}>
                      {backtestResult.key_metrics.status}
                    </Text>
                  </Grid.Col>
                </Grid>
              </Box>

              <Divider />

              {/* Portfolio Performance */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Portfolio Performance
                </Text>
                <Grid>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Market Value
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.market_value}
                        prefix="$"
                        thousandSeparator
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Peak Equity
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.peak_equity}
                        prefix="$"
                        thousandSeparator
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Cash Injection
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.cash_injection}
                        prefix="$"
                        thousandSeparator
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Net Realized PnL
                    </Text>
                    <Text
                      size="lg"
                      fw={600}
                      c={
                        backtestResult.key_metrics.net_realized_pnl >= 0
                          ? "green"
                          : "red"
                      }
                    >
                      <NumberFormatter
                        value={backtestResult.key_metrics.net_realized_pnl}
                        prefix="$"
                        thousandSeparator
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                </Grid>
              </Box>

              <Divider />

              {/* Return Metrics */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Return Metrics
                </Text>
                <Grid>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Gross Return
                    </Text>
                    <Text
                      size="lg"
                      fw={600}
                      c={
                        backtestResult.key_metrics.gross_return >= 0
                          ? "green"
                          : "red"
                      }
                    >
                      <NumberFormatter
                        value={backtestResult.key_metrics.gross_return * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Net Return
                    </Text>
                    <Text
                      size="lg"
                      fw={600}
                      c={
                        backtestResult.key_metrics.net_return >= 0
                          ? "green"
                          : "red"
                      }
                    >
                      <NumberFormatter
                        value={backtestResult.key_metrics.net_return * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Ann. Return
                    </Text>
                    <Text
                      size="lg"
                      fw={600}
                      c={
                        backtestResult.key_metrics.annualized_return >= 0
                          ? "green"
                          : "red"
                      }
                    >
                      <NumberFormatter
                        value={
                          backtestResult.key_metrics.annualized_return * 100
                        }
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Win Rate
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.win_rate * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Profit Factor
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.profit_factor}
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                </Grid>
              </Box>

              <Divider />

              {/* Risk Metrics */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Risk Metrics (rf: {backtestResult.key_metrics.risk_free_rate})
                </Text>
                <Grid>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Sharpe
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.sharpe_ratio}
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Sortino
                    </Text>
                    <Text size="lg" fw={600}>
                      <NumberFormatter
                        value={backtestResult.key_metrics.sortino_ratio}
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Calmar
                    </Text>
                    <Text size="lg" fw={600}>
                      {Number.isFinite(
                        backtestResult.key_metrics.calmar_ratio
                      ) ? (
                        <NumberFormatter
                          value={backtestResult.key_metrics.calmar_ratio}
                          decimalScale={2}
                        />
                      ) : (
                        <span style={{ color: "black" }}>-</span>
                      )}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={2.4}>
                    <Text size="sm" c="dimmed" mb="xs">
                      Max DD
                    </Text>
                    <Text size="lg" fw={600} c="red">
                      <NumberFormatter
                        value={backtestResult.key_metrics.max_drawdown * 100}
                        suffix="%"
                        decimalScale={2}
                      />
                    </Text>
                  </Grid.Col>
                </Grid>
              </Box>

              <Divider />

              {/* Position Performance */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Position Performance
                </Text>
                <Stack gap="md">
                  {backtestResult.key_metrics.position_metrics.map(
                    (position, index) => (
                      <Box key={index}>
                        <Text
                          size="sm"
                          fw={600}
                          mb="xs"
                          style={{
                            color:
                              index === 0
                                ? THEME_A_COLORS.primary.blue
                                : index === 1
                                ? THEME_A_COLORS.primary.gold
                                : index === 2
                                ? THEME_A_COLORS.system.teal
                                : index === 3
                                ? THEME_A_COLORS.system.pink
                                : index === 4
                                ? THEME_A_COLORS.system.orange
                                : THEME_A_COLORS.system.lightBlue,
                          }}
                        >
                          {backtestResult.tickers[index]}
                        </Text>

                        {/* First line: Realized PnL, Unrealized PnL, Alpha, Beta */}
                        <Grid mb="xs">
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Realized PnL
                            </Text>
                            <Text
                              size="lg"
                              fw={600}
                              c={
                                position.realized_pnl_net >= 0 ? "green" : "red"
                              }
                            >
                              <NumberFormatter
                                value={position.realized_pnl_net}
                                prefix="$"
                                thousandSeparator
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Unrealized PnL
                            </Text>
                            <Text
                              size="lg"
                              fw={600}
                              c={
                                position.unrealized_pnl_net >= 0
                                  ? "green"
                                  : "red"
                              }
                            >
                              <NumberFormatter
                                value={position.unrealized_pnl_net}
                                prefix="$"
                                thousandSeparator
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Alpha
                            </Text>
                            <Text size="lg" fw={600}>
                              {Number.isFinite(position.alpha) ? (
                                "N/A"
                              ) : (
                                // <NumberFormatter
                                //   value={position.alpha}
                                //   decimalScale={4}
                                // />
                                <span style={{ color: "black" }}>-</span>
                              )}
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Beta
                            </Text>
                            <Text size="lg" fw={600}>
                              {Number.isFinite(position.beta) ? (
                                // <NumberFormatter
                                //   value={position.beta}
                                //   decimalScale={4}
                                // />
                                "N/A"
                              ) : (
                                <span style={{ color: "black" }}>-</span>
                              )}
                            </Text>
                          </Grid.Col>
                        </Grid>

                        {/* Second line: Gross Return, Net Return, Ann. Return, Win Rate, Profit Factor */}
                        <Grid mb="xs">
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Gross Return
                            </Text>
                            <Text
                              size="lg"
                              fw={600}
                              c={position.gross_return >= 0 ? "green" : "red"}
                            >
                              <NumberFormatter
                                value={position.gross_return * 100}
                                suffix="%"
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Net Return
                            </Text>
                            <Text
                              size="lg"
                              fw={600}
                              c={position.net_return >= 0 ? "green" : "red"}
                            >
                              <NumberFormatter
                                value={position.net_return * 100}
                                suffix="%"
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Ann. Return
                            </Text>
                            <Text
                              size="lg"
                              fw={600}
                              c={
                                position.annualized_return >= 0
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
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Win Rate
                            </Text>
                            <Text size="lg" fw={600}>
                              <NumberFormatter
                                value={position.win_rate * 100}
                                suffix="%"
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                          <Grid.Col span={2.4}>
                            <Text size="sm" c="dimmed" mb="xs">
                              Profit Factor
                            </Text>
                            <Text size="lg" fw={600}>
                              <NumberFormatter
                                value={position.profit_factor}
                                decimalScale={2}
                              />
                            </Text>
                          </Grid.Col>
                        </Grid>

                        {/* Trade Statistics Table */}
                        <Box mt="lg">
                          <Text size="sm" c="dimmed" mb="xs">
                            Trade Type Breakdown
                          </Text>
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
                              style={{
                                borderBottom: `1px solid ${THEME_A_COLORS.system.gray}`,
                              }}
                              m={0}
                            >
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" fw={500}>
                                  Take Profit
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs">
                                  {(
                                    position.take_profit_trades_pct * 100
                                  ).toFixed(1)}
                                  %
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                            </Grid>

                            {/* Stop Loss Row */}
                            <Grid
                              style={{
                                borderBottom: `1px solid ${THEME_A_COLORS.system.gray}`,
                              }}
                              m={0}
                            >
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" fw={500}>
                                  Stop Loss
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs">
                                  {(
                                    position.stop_loss_trades_pct * 100
                                  ).toFixed(1)}
                                  %
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                            </Grid>

                            {/* Signal Sell Row */}
                            <Grid
                              style={{
                                borderBottom: `1px solid ${THEME_A_COLORS.system.gray}`,
                              }}
                              m={0}
                            >
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" fw={500}>
                                  Signal Sell
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs">
                                  {(
                                    position.signal_sell_trades_pct *
                                    position.sell_pct *
                                    100
                                  ).toFixed(1)}
                                  %
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                            </Grid>

                            {/* Signal Buy Row */}
                            <Grid m={0}>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" fw={500}>
                                  Signal Buy
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs">
                                  {(position.buy_pct * 100).toFixed(1)}%
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                              <Grid.Col span={3} p="xs">
                                <Text size="xs" style={{ color: "black" }}>
                                  -
                                </Text>
                              </Grid.Col>
                            </Grid>
                          </Box>
                        </Box>
                      </Box>
                    )
                  )}
                </Stack>
              </Box>
            </Stack>
          </Collapse>
        </Fieldset>
      )}

      {/* The Curves */}
      {backtestResult && (
        <Fieldset
          legend={
            <Group gap="xs" justify="space-between" style={{ width: "100%" }}>
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                The Curves
              </Text>
              <Button
                variant="subtle"
                size="xs"
                onClick={() => setCurvesOpened(!curvesOpened)}
                style={{
                  padding: "2px 6px",
                  height: "auto",
                  fontSize: "12px",
                  minWidth: "auto",
                  color: MANTINE_THEME_A_COLORS.teal,
                  marginLeft: "auto",
                }}
              >
                {curvesOpened ? "Hide" : "Show"}
              </Button>
            </Group>
          }
        >
          <Collapse in={curvesOpened}>
            <Stack gap="lg">
              {/* Chart 1: Notional, Equity, and Cash Curves */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Portfolio Value Curves
                </Text>
                <LineChart
                  data={[
                    {
                      name: "Notional",
                      data: backtestResult.timestamps.map((time, index) => ({
                        time,
                        value: backtestResult.notional_curve[index],
                      })),
                      color: THEME_A_COLORS.primary.blue,
                    },
                    {
                      name: "Equity",
                      data: backtestResult.timestamps.map((time, index) => ({
                        time,
                        value: backtestResult.equity_curve[index],
                      })),
                      color: THEME_A_COLORS.primary.gold,
                    },
                    {
                      name: "Cash",
                      data: backtestResult.timestamps.map((time, index) => ({
                        time,
                        value: backtestResult.cash_curve[index],
                      })),
                      color: THEME_A_COLORS.system.teal,
                    },
                  ]}
                  height={300}
                />
              </Box>

              {/* Chart 2: Cost Curve */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  Cost Curve
                </Text>
                <LineChart
                  data={[
                    {
                      name: "Cumulative Cost",
                      data: backtestResult.timestamps.map((time, index) => {
                        // Compute running sum (cumulative cost)
                        let cumulative = 0;
                        for (let i = 0; i <= index; i++) {
                          cumulative += backtestResult.cost_curve[i] || 0;
                        }
                        return {
                          time,
                          value: cumulative,
                        };
                      }),
                      color: THEME_A_COLORS.tertiary.cyan,
                    },
                  ]}
                  height={300}
                />
              </Box>

              {/* Chart 3: PnL Curves */}
              <Box>
                <Text size="sm" c="dimmed" mb="xs" fw={500}>
                  PnL Curves
                </Text>
                <LineChart
                  data={[
                    {
                      name: "Cumulative Realized PnL",
                      data: backtestResult.timestamps.map((time, index) => {
                        // Compute running sum (cumulative realized PnL)
                        let cumulative = 0;
                        for (let i = 0; i <= index; i++) {
                          cumulative +=
                            backtestResult.realized_pnl_curve[i] || 0;
                        }
                        return {
                          time,
                          value: cumulative,
                        };
                      }),
                      color: THEME_C_COLORS.core.primaryRed,
                    },
                    // Dummy series for legend spacing
                    {
                      name: "",
                      data:
                        backtestResult.timestamps.length > 0
                          ? [{ time: backtestResult.timestamps[0], value: 0 }]
                          : [],
                      color: "rgba(0,0,0,0)",
                    },
                    {
                      name: "Unrealized PnL",
                      data: backtestResult.timestamps.map((time, index) => ({
                        time,
                        value: backtestResult.unrealized_pnl_curve[index],
                      })),
                      color: THEME_A_COLORS.system.lightBlue,
                    },
                  ]}
                  height={300}
                />
              </Box>
            </Stack>
          </Collapse>
        </Fieldset>
      )}
    </Stack>
  );
}
