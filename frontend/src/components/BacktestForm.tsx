import {
  Button,
  Fieldset,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { DateTime } from "luxon";
import type { BacktestParams } from "../types/backtest";
import { defaultBacktestParams } from "../types/backtest";

interface BacktestFormProps {
  onSubmit: (params: BacktestParams) => void;
  loading?: boolean;
}

export function BacktestForm({ onSubmit, loading = false }: BacktestFormProps) {
  const form = useForm<BacktestParams>({
    initialValues: defaultBacktestParams,
    validate: {
      strategy_name: (value) =>
        value.length < 1 ? "Strategy name is required" : null,
      portfolio_name: (value) =>
        value.length < 1 ? "Portfolio name is required" : null,
      start: (value) => (!value ? "Start date is required" : null),
      end: (value) => (!value ? "End date is required" : null),
      warm_up_period: (value) =>
        value < 0 ? "Warm up period must be positive" : null,
      cadence: (value) =>
        value < 1 ? "Cadence must be at least 1 minute" : null,
      portfolio_params: {
        initial_cash: (value) =>
          value <= 0 ? "Initial cash must be positive" : null,
      },
    },
  });

  const handleSubmit = (values: BacktestParams) => {
    // Convert dates to ISO format for the backend
    const submitValues = {
      ...values,
      start: values.start
        ? DateTime.fromFormat(values.start, "yyyy-MM-dd").toISO()!
        : "",
      end: values.end
        ? DateTime.fromFormat(values.end, "yyyy-MM-dd").toISO()!
        : "",
    };
    onSubmit(submitValues);
  };

  const handleTestEmpty = () => {
    // Send empty params for testing
    const emptyParams: BacktestParams = {
      strategy_name: "",
      portfolio_name: "",
      start: "",
      end: "",
      strategies: {},
      portfolio_params: {
        initial_cash: 0,
        capital_growth_pct: 0,
        capital_growth_amount: 0,
        capital_growth_frequency: "Daily",
      },
      portfolio_constraints_params: {
        rebalance_threshold_pct: 0,
        min_cash_pct: 0,
        max_drawdown_pct: 0,
      },
      position_constraints_params: [],
      warm_up_period: 0,
      cadence: 0,
    };
    onSubmit(emptyParams);
  };

  return (
    <form onSubmit={form.onSubmit(handleSubmit)}>
      <Stack gap="md">
        <Fieldset legend="Basic Configuration">
          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Strategy Name"
                placeholder="Enter strategy name"
                {...form.getInputProps("strategy_name")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Portfolio Name"
                placeholder="Enter portfolio name"
                {...form.getInputProps("portfolio_name")}
              />
            </Grid.Col>
          </Grid>
        </Fieldset>

        <Fieldset legend="Time Range">
          <Grid>
            <Grid.Col span={6}>
              <DatePickerInput
                label="Start Date"
                placeholder="Select start date"
                clearable
                valueFormat="MM/DD/YYYY"
                {...form.getInputProps("start")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <DatePickerInput
                label="End Date"
                placeholder="Select end date"
                clearable
                valueFormat="MM/DD/YYYY"
                {...form.getInputProps("end")}
              />
            </Grid.Col>
          </Grid>
        </Fieldset>

        <Fieldset legend="Portfolio Parameters">
          <Grid>
            <Grid.Col span={6}>
              <NumberInput
                label="Initial Cash"
                placeholder="Enter initial cash amount"
                min={0}
                {...form.getInputProps("portfolio_params.initial_cash")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <NumberInput
                label="Capital Growth %"
                placeholder="Enter capital growth percentage"
                min={0}
                max={100}
                step={0.01}
                {...form.getInputProps("portfolio_params.capital_growth_pct")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <NumberInput
                label="Capital Growth Amount"
                placeholder="Enter capital growth amount"
                min={0}
                {...form.getInputProps(
                  "portfolio_params.capital_growth_amount"
                )}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <Select
                label="Capital Growth Frequency"
                placeholder="Select frequency"
                data={[
                  { value: "Daily", label: "Daily" },
                  { value: "Weekly", label: "Weekly" },
                  { value: "Monthly", label: "Monthly" },
                  { value: "Quarterly", label: "Quarterly" },
                  { value: "Yearly", label: "Yearly" },
                ]}
                {...form.getInputProps(
                  "portfolio_params.capital_growth_frequency"
                )}
              />
            </Grid.Col>
          </Grid>
        </Fieldset>

        <Fieldset legend="Portfolio Constraints">
          <Grid>
            <Grid.Col span={4}>
              <NumberInput
                label="Rebalance Threshold %"
                placeholder="Enter rebalance threshold"
                min={0}
                step={0.01}
                {...form.getInputProps(
                  "portfolio_constraints_params.rebalance_threshold_pct"
                )}
              />
            </Grid.Col>
            <Grid.Col span={4}>
              <NumberInput
                label="Min Cash %"
                placeholder="Enter minimum cash percentage"
                min={0}
                step={0.01}
                {...form.getInputProps(
                  "portfolio_constraints_params.min_cash_pct"
                )}
              />
            </Grid.Col>
            <Grid.Col span={4}>
              <NumberInput
                label="Max Drawdown %"
                placeholder="Enter max drawdown percentage"
                min={0}
                step={0.01}
                {...form.getInputProps(
                  "portfolio_constraints_params.max_drawdown_pct"
                )}
              />
            </Grid.Col>
          </Grid>
        </Fieldset>

        <Fieldset legend="Execution Parameters">
          <Grid>
            <Grid.Col span={6}>
              <NumberInput
                label="Warm Up Period"
                placeholder="Enter warm up period"
                min={0}
                {...form.getInputProps("warm_up_period")}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <NumberInput
                label="Cadence (minutes)"
                placeholder="Enter cadence in minutes"
                min={1}
                {...form.getInputProps("cadence")}
              />
            </Grid.Col>
          </Grid>
        </Fieldset>

        <Fieldset legend="Strategies (Pre-configured)">
          <Textarea
            label="Strategies Configuration"
            description="Mock strategies are pre-loaded for BTC-USD and ETH-USD with EMA/RSI/MACD signals. You can modify this JSON if needed."
            placeholder='{"BTC-USD": [{"EmaRsiMacd": {"ema_fast": 12, ...}}]}'
            minRows={50}
            value={JSON.stringify(form.values.strategies, null, 2)}
            onChange={(event) => {
              try {
                const parsed = JSON.parse(event.currentTarget.value);
                form.setFieldValue("strategies", parsed);
              } catch {
                // Invalid JSON, but keep the text for editing
              }
            }}
          />
        </Fieldset>

        <Group justify="flex-end" gap="sm">
          <Button variant="outline" onClick={handleTestEmpty} loading={loading}>
            Test Empty Params
          </Button>
          <Button type="submit" loading={loading}>
            Run Backtest
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
