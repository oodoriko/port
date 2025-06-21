import {
  Box,
  Card,
  Grid,
  Group,
  NumberFormatter,
  Progress,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconArrowDown,
  IconArrowUp,
  IconTrendingUp,
} from "@tabler/icons-react";
import type { BacktestResult } from "../types/backtest";
import { PortfolioCurves } from "./PortfolioCurves";

interface BacktestResultsProps {
  results: BacktestResult;
}

export function BacktestResults({ results }: BacktestResultsProps) {
  const {
    backtest_id,
    initial_value,
    final_value,
    total_return,
    max_value,
    min_value,
    peak_notional,
  } = results;

  const isPositiveReturn = total_return >= 0;
  const returnIcon = isPositiveReturn ? (
    <IconArrowUp size={16} />
  ) : (
    <IconArrowDown size={16} />
  );
  const returnColor = isPositiveReturn ? "green" : "red";

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Backtest ID: {backtest_id}
      </Text>

      <Grid>
        <Grid.Col span={12}>
          <Card shadow="xs" padding="md" radius="sm">
            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">
                Total Return
              </Text>
              {returnIcon}
            </Group>
            <Group align="flex-end" gap="xs">
              <Text size="xl" fw={700} c={returnColor}>
                <NumberFormatter
                  value={total_return}
                  suffix="%"
                  decimalScale={2}
                />
              </Text>
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={6}>
          <Card shadow="xs" padding="md" radius="sm">
            <Text size="sm" c="dimmed" mb="xs">
              Initial Value
            </Text>
            <Text size="lg" fw={600}>
              <NumberFormatter
                value={initial_value}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={6}>
          <Card shadow="xs" padding="md" radius="sm">
            <Text size="sm" c="dimmed" mb="xs">
              Final Value
            </Text>
            <Text size="lg" fw={600}>
              <NumberFormatter
                value={final_value}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={6}>
          <Card shadow="xs" padding="md" radius="sm">
            <Text size="sm" c="dimmed" mb="xs">
              Max Value
            </Text>
            <Text size="lg" fw={600} c="green">
              <NumberFormatter
                value={max_value}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={6}>
          <Card shadow="xs" padding="md" radius="sm">
            <Text size="sm" c="dimmed" mb="xs">
              Min Value
            </Text>
            <Text size="lg" fw={600} c="red">
              <NumberFormatter
                value={min_value}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Card>
        </Grid.Col>

        <Grid.Col span={12}>
          <Card shadow="xs" padding="md" radius="sm">
            <Group justify="space-between" mb="xs">
              <Text size="sm" c="dimmed">
                High-Water Mark
              </Text>
              <IconTrendingUp size={16} />
            </Group>
            <Text size="lg" fw={600}>
              <NumberFormatter
                value={peak_notional}
                prefix="$"
                thousandSeparator
                decimalScale={2}
              />
            </Text>
          </Card>
        </Grid.Col>
      </Grid>

      {/* Simple equity curve visualization */}
      <Card shadow="xs" padding="md" radius="sm">
        <Text size="sm" c="dimmed" mb="md">
          Performance Overview
        </Text>
        <Box>
          <Group justify="space-between" mb="xs">
            <Text size="xs" c="dimmed">
              Portfolio Growth
            </Text>
            <Text size="xs" c="dimmed">
              {isPositiveReturn ? "Profit" : "Loss"}
            </Text>
          </Group>
          <Progress
            value={Math.abs(total_return)}
            color={returnColor}
            size="lg"
            radius="md"
          />
        </Box>
      </Card>

      {/* Portfolio Performance Curves */}
      <PortfolioCurves results={results} />
    </Stack>
  );
}
