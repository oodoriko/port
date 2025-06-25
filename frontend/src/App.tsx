import {
  Badge,
  Box,
  Container,
  Grid,
  Group,
  LoadingOverlay,
  NumberFormatter,
  Paper,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { runBacktest } from "./api/backtest";
import { BacktestDetails } from "./components/BacktestDetails";
import { BacktestForm } from "./components/BacktestForm";
import { BacktestResults } from "./components/BacktestResults";
import type { BacktestParams, BacktestResult } from "./types/backtest";

function App() {
  console.log("🚀 App component is rendering!");

  const [results, setResults] = useState<BacktestResult | null>(null);
  const [backtestParams, setBacktestParams] = useState<BacktestParams | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string | null>("backtest");

  const handleBacktest = async (params: BacktestParams) => {
    setLoading(true);
    setBacktestParams(params);
    try {
      const result = await runBacktest(params);
      setResults(result);
      notifications.show({
        title: "Backtest Complete",
        message: "Backtest has been successfully executed",
        color: "green",
      });
    } catch (error) {
      notifications.show({
        title: "Backtest Failed",
        message:
          error instanceof Error ? error.message : "An unknown error occurred",
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        <Box>
          <Title order={1} mb="md">
            🩴🩱🌊🐬🪼🧢🧊
          </Title>
          <Text c="dimmed">
            {/* 吾輩はサトシである🐳 */}
            夏休み!夏休み!夏休み!夏休み!夏休み!夏休み!夏休み!夏休み!!!!!! ねぇ
            summertime~ 海岸通りを歩きたい~
          </Text>
        </Box>
        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="backtest">Backtest Runner</Tabs.Tab>
            <Tabs.Tab value="details">Backtest Details</Tabs.Tab>
            <Tabs.Tab value="charts">Price Charts</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="backtest" mt="xl">
            <Grid>
              <Grid.Col span={{ base: 12, md: 6 }}>
                <Paper shadow="sm" p="lg" radius="md" pos="relative">
                  <LoadingOverlay visible={loading} />
                  <Group justify="space-between" align="center" mb="md">
                    <Title order={2} size="h3" m={0}>
                      Configuration
                    </Title>
                    <Box w={100} /> {/* dummy element to match badge height */}
                  </Group>
                  <BacktestForm onSubmit={handleBacktest} loading={loading} />
                </Paper>
              </Grid.Col>

              <Grid.Col span={{ base: 12, md: 6 }}>
                <Paper shadow="sm" p="lg" radius="md" pos="relative">
                  <Group justify="space-between" align="center" mb="md">
                    <Title order={2} size="h3" m={0}>
                      Results
                    </Title>
                    {results ? (
                      <Badge variant="light" size="sm">
                        <NumberFormatter
                          value={results.total_records}
                          thousandSeparator
                        />{" "}
                        records
                      </Badge>
                    ) : (
                      <Box w={100} />
                    )}
                  </Group>
                  {results ? (
                    <BacktestResults results={results} />
                  ) : (
                    // <BacktestKeyMetrics results={results} />
                    <Text c="dimmed" ta="center" py="xl">
                      Run a backtest to see results here
                    </Text>
                  )}
                </Paper>
              </Grid.Col>
            </Grid>
          </Tabs.Panel>

          <Tabs.Panel value="details" mt="xl">
            <Paper shadow="sm" p="lg" radius="md">
              <Group justify="space-between" align="center" mb="md">
                <Title order={2} size="h3" m={0}>
                  Backtest Configuration Details
                </Title>
                {backtestParams ? (
                  <Badge variant="light" size="sm">
                    {backtestParams.strategy_name}
                  </Badge>
                ) : (
                  <Box w={100} />
                )}
              </Group>
              {backtestParams ? (
                <BacktestDetails
                  backtestParams={backtestParams}
                  backtestResult={results || undefined}
                />
              ) : (
                <Text c="dimmed" ta="center" py="xl">
                  Run a backtest to see configuration details here
                </Text>
              )}
            </Paper>
          </Tabs.Panel>

          {/* <Tabs.Panel value="charts" mt="xl">
            <TradingViewChart />
          </Tabs.Panel> */}
        </Tabs>
      </Stack>
    </Container>
  );
}

export default App;
