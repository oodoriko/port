import {
  Accordion,
  Badge,
  Card,
  Divider,
  Grid,
  Group,
  NumberFormatter,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconArrowDown,
  IconArrowUp,
  IconChartBar,
  IconCheck,
  IconHourglass,
  IconTarget,
  IconTrendingUp,
  IconX,
} from "@tabler/icons-react";
import type { BacktestResult } from "../types/backtest";

interface BacktestKeyMetricsProps {
  results: BacktestResult;
}

export function BacktestKeyMetrics({ results }: BacktestKeyMetricsProps) {
  const { position_performances, trade_metrics } = results;

  if (!position_performances && !trade_metrics) {
    return (
      <Card shadow="xs" padding="md" radius="sm">
        <Text size="sm" c="dimmed" ta="center">
          No detailed metrics available for this backtest
        </Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      {/* Overall Performance Summary */}
      <Card shadow="xs" padding="md" radius="sm">
        <Group justify="space-between" mb="md">
          <Text size="lg" fw={600}>
            📊 Key Performance Metrics
          </Text>
          <IconChartBar size={20} />
        </Group>

        <Grid>
          <Grid.Col span={6}>
            <Text size="sm" c="dimmed" mb="xs">
              Total Return
            </Text>
            <Group align="flex-end" gap="xs">
              <Text
                size="xl"
                fw={700}
                c={results.total_return >= 0 ? "green" : "red"}
              >
                <NumberFormatter
                  value={results.total_return}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
              {results.total_return >= 0 ? (
                <IconArrowUp size={16} color="green" />
              ) : (
                <IconArrowDown size={16} color="red" />
              )}
            </Group>
          </Grid.Col>

          <Grid.Col span={6}>
            <Text size="sm" c="dimmed" mb="xs">
              Peak Equity
            </Text>
            <Text size="xl" fw={700}>
              <NumberFormatter
                value={results.peak_equity}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Grid.Col>
        </Grid>
      </Card>

      {/* Trade Metrics */}
      {trade_metrics && (
        <Card shadow="xs" padding="md" radius="sm">
          <Group justify="space-between" mb="md">
            <Text size="lg" fw={600}>
              🎯 Trading Performance
            </Text>
            <IconTarget size={20} />
          </Group>

          <Grid>
            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Total Trades
              </Text>
              <Text size="lg" fw={600}>
                {trade_metrics.total_trades}
              </Text>
            </Grid.Col>

            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Buy/Sell Ratio
              </Text>
              <Text size="lg" fw={600}>
                {trade_metrics.total_buy_trades}/
                {trade_metrics.total_sell_trades}
              </Text>
            </Grid.Col>

            <Grid.Col span={4}>
              <Text size="sm" c="dimmed" mb="xs">
                Overall Win Rate
              </Text>
              <Text
                size="lg"
                fw={600}
                c={trade_metrics.overall_win_rate >= 50 ? "green" : "red"}
              >
                <NumberFormatter
                  value={trade_metrics.overall_win_rate}
                  suffix="%"
                  decimalScale={1}
                />
              </Text>
            </Grid.Col>
          </Grid>

          <Divider my="md" />

          <Grid>
            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Avg Gross Return
              </Text>
              <Text
                size="lg"
                fw={600}
                c={
                  trade_metrics.overall_avg_gross_return >= 0 ? "green" : "red"
                }
              >
                <NumberFormatter
                  value={trade_metrics.overall_avg_gross_return * 100}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>

            <Grid.Col span={6}>
              <Text size="sm" c="dimmed" mb="xs">
                Avg Net Return
              </Text>
              <Text
                size="lg"
                fw={600}
                c={trade_metrics.overall_avg_net_return >= 0 ? "green" : "red"}
              >
                <NumberFormatter
                  value={trade_metrics.overall_avg_net_return * 100}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {/* Position Performance */}
      {position_performances && position_performances.length > 0 && (
        <Card shadow="xs" padding="md" radius="sm">
          <Group justify="space-between" mb="md">
            <Text size="lg" fw={600}>
              📈 Position Performance
            </Text>
            <IconTrendingUp size={20} />
          </Group>

          <Accordion variant="contained">
            {position_performances.map((position) => (
              <Accordion.Item
                key={position.ticker_id}
                value={`position-${position.ticker_id}`}
              >
                <Accordion.Control>
                  <Group justify="space-between">
                    <Text fw={500}>{position.ticker_name}</Text>
                    <Group gap="xs">
                      <Badge
                        color={
                          position.position_status === "Open" ? "blue" : "gray"
                        }
                        variant="light"
                      >
                        {position.position_status}
                      </Badge>
                      <Badge
                        color={position.realized_pnl >= 0 ? "green" : "red"}
                        variant="light"
                      >
                        <NumberFormatter
                          value={position.realized_pnl}
                          prefix="$"
                          decimalScale={2}
                        />
                      </Badge>
                    </Group>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Grid>
                    <Grid.Col span={6}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Quantity
                      </Text>
                      <Text size="md" fw={600}>
                        <NumberFormatter
                          value={position.quantity}
                          decimalScale={4}
                        />
                      </Text>
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Realized Ratio
                      </Text>
                      <Text size="md" fw={600}>
                        <NumberFormatter
                          value={position.realized_ratio * 100}
                          suffix="%"
                          decimalScale={1}
                        />
                      </Text>
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Gross Realized Return
                      </Text>
                      <Text
                        size="md"
                        fw={600}
                        c={
                          position.gross_realized_return >= 0 ? "green" : "red"
                        }
                      >
                        <NumberFormatter
                          value={position.gross_realized_return * 100}
                          suffix="%"
                          decimalScale={2}
                        />
                      </Text>
                    </Grid.Col>

                    <Grid.Col span={6}>
                      <Text size="sm" c="dimmed" mb="xs">
                        Net Realized Return
                      </Text>
                      <Text
                        size="md"
                        fw={600}
                        c={position.net_realized_return >= 0 ? "green" : "red"}
                      >
                        <NumberFormatter
                          value={position.net_realized_return * 100}
                          suffix="%"
                          decimalScale={2}
                        />
                      </Text>
                    </Grid.Col>
                  </Grid>

                  <Divider my="md" />

                  <Text size="sm" fw={600} mb="xs">
                    Trade Type Breakdown:
                  </Text>
                  <Grid>
                    <Grid.Col span={4}>
                      <Text size="xs" c="dimmed">
                        Take Profit
                      </Text>
                      <Group gap="xs">
                        <IconArrowUp size={12} color="green" />
                        <Text size="sm">
                          <NumberFormatter
                            value={position.take_profit_gain_pct}
                            suffix="%"
                            decimalScale={1}
                          />
                        </Text>
                      </Group>
                    </Grid.Col>

                    <Grid.Col span={4}>
                      <Text size="xs" c="dimmed">
                        Stop Loss
                      </Text>
                      <Group gap="xs">
                        <IconArrowDown size={12} color="red" />
                        <Text size="sm">
                          <NumberFormatter
                            value={position.stop_loss_loss_pct}
                            suffix="%"
                            decimalScale={1}
                          />
                        </Text>
                      </Group>
                    </Grid.Col>

                    <Grid.Col span={4}>
                      <Text size="xs" c="dimmed">
                        Signal Sell
                      </Text>
                      <Group gap="xs">
                        <IconTarget size={12} color="blue" />
                        <Text size="sm">
                          <NumberFormatter
                            value={position.signal_sell_gain_pct}
                            suffix="%"
                            decimalScale={1}
                          />
                        </Text>
                      </Group>
                    </Grid.Col>
                  </Grid>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Card>
      )}

      {/* Per-Ticker Trade Metrics */}
      {trade_metrics &&
        Object.keys(trade_metrics.ticker_metrics).length > 0 && (
          <Card shadow="xs" padding="md" radius="sm">
            <Group justify="space-between" mb="md">
              <Text size="lg" fw={600}>
                📊 Per-Ticker Trade Analysis
              </Text>
              <IconChartBar size={20} />
            </Group>

            <Accordion variant="contained">
              {Object.entries(trade_metrics.ticker_metrics).map(
                ([tickerId, metrics]) => (
                  <Accordion.Item key={tickerId} value={`ticker-${tickerId}`}>
                    <Accordion.Control>
                      <Group justify="space-between">
                        <Text fw={500}>{metrics.ticker_name}</Text>
                        <Group gap="xs">
                          <Badge color="blue" variant="light">
                            {metrics.total_trades} trades
                          </Badge>
                          <Badge
                            color={metrics.win_rate >= 50 ? "green" : "red"}
                            variant="light"
                          >
                            <NumberFormatter
                              value={metrics.win_rate}
                              suffix="%"
                              decimalScale={1}
                            />
                          </Badge>
                        </Group>
                      </Group>
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Grid>
                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Avg Trades/Day
                          </Text>
                          <Text size="md" fw={600}>
                            <NumberFormatter
                              value={metrics.avg_trades_per_day}
                              decimalScale={2}
                            />
                          </Text>
                        </Grid.Col>

                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Trading Days
                          </Text>
                          <Text size="md" fw={600}>
                            {metrics.trading_days}
                          </Text>
                        </Grid.Col>

                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Buy/Sell Ratio
                          </Text>
                          <Text size="md" fw={600}>
                            {metrics.buy_trades}/{metrics.sell_trades}
                          </Text>
                        </Grid.Col>

                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Avg Holding Period
                          </Text>
                          <Text size="md" fw={600}>
                            <NumberFormatter
                              value={metrics.avg_holding_period_minutes / 60}
                              suffix=" hours"
                              decimalScale={1}
                            />
                          </Text>
                        </Grid.Col>

                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Avg Gross Return
                          </Text>
                          <Text
                            size="md"
                            fw={600}
                            c={metrics.avg_gross_return >= 0 ? "green" : "red"}
                          >
                            <NumberFormatter
                              value={metrics.avg_gross_return * 100}
                              suffix="%"
                              decimalScale={2}
                            />
                          </Text>
                        </Grid.Col>

                        <Grid.Col span={6}>
                          <Text size="sm" c="dimmed" mb="xs">
                            Avg Net Return
                          </Text>
                          <Text
                            size="md"
                            fw={600}
                            c={metrics.avg_net_return >= 0 ? "green" : "red"}
                          >
                            <NumberFormatter
                              value={metrics.avg_net_return * 100}
                              suffix="%"
                              decimalScale={2}
                            />
                          </Text>
                        </Grid.Col>
                      </Grid>

                      <Divider my="md" />

                      <Text size="sm" fw={600} mb="xs">
                        Trade Status:
                      </Text>
                      <Grid>
                        <Grid.Col span={3}>
                          <Group gap="xs">
                            <IconCheck size={12} color="green" />
                            <Text size="sm">
                              Executed: {metrics.executed_pct.toFixed(1)}%
                            </Text>
                          </Group>
                        </Grid.Col>

                        <Grid.Col span={3}>
                          <Group gap="xs">
                            <IconX size={12} color="red" />
                            <Text size="sm">
                              Failed: {metrics.failed_pct.toFixed(1)}%
                            </Text>
                          </Group>
                        </Grid.Col>

                        <Grid.Col span={3}>
                          <Group gap="xs">
                            <IconAlertTriangle size={12} color="orange" />
                            <Text size="sm">
                              Rejected: {metrics.rejected_pct.toFixed(1)}%
                            </Text>
                          </Group>
                        </Grid.Col>

                        <Grid.Col span={3}>
                          <Group gap="xs">
                            <IconHourglass size={12} color="blue" />
                            <Text size="sm">
                              Pending: {metrics.pending_pct.toFixed(1)}%
                            </Text>
                          </Group>
                        </Grid.Col>
                      </Grid>
                    </Accordion.Panel>
                  </Accordion.Item>
                )
              )}
            </Accordion>
          </Card>
        )}
    </Stack>
  );
}
