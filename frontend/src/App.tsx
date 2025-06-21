import {
  Badge,
  Box,
  Container,
  Grid,
  Group,
  LoadingOverlay,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { runBacktest } from "./api/backtest";
import { BacktestForm } from "./components/BacktestForm";
import { BacktestResults } from "./components/BacktestResults";
import type { BacktestParams, BacktestResult } from "./types/backtest";

function App() {
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleBacktest = async (params: BacktestParams) => {
    setLoading(true);
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
            Backtest Runner
          </Title>
          <Text c="dimmed">
            Todo: cache data online, cache backtest results, live trading view,
            strategy view
          </Text>
        </Box>

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
                    {results.total_records} records
                  </Badge>
                ) : (
                  <Box w={100} /> // keep layout consistent if no results
                )}
              </Group>
              {results ? (
                <BacktestResults results={results} />
              ) : (
                <Text c="dimmed" ta="center" py="xl">
                  Run a backtest to see results here
                </Text>
              )}
            </Paper>
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}

export default App;
