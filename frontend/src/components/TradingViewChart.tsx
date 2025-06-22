import {
  Badge,
  Button,
  Group,
  LoadingOverlay,
  Paper,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useRef, useState } from "react";
import { DataAPI } from "../api/data";
import { THEME_C_COLORS } from "../theme/theme_c";

// Time range configuration
type TimeRange = "1D" | "7D" | "1M" | "6M" | "1Y" | "5Y" | "All";

interface TimeRangeConfig {
  days: number;
  label: string;
}

const TIME_RANGES: Record<TimeRange, TimeRangeConfig> = {
  "1D": { days: 1, label: "1D" },
  "7D": { days: 7, label: "7D" },
  "1M": { days: 30, label: "1M" },
  "6M": { days: 180, label: "6M" },
  "1Y": { days: 365, label: "1Y" },
  "5Y": { days: 1825, label: "5Y" },
  All: { days: 10000, label: "All" },
};

// Optimal data point limits for minute-level data
const DATA_POINT_LIMITS: Record<TimeRange, number> = {
  "1D": 288, // ~5-minute intervals (1440 minutes / 5)
  "7D": 336, // ~30-minute intervals (10080 minutes / 30)
  "1M": 720, // ~1-hour intervals (43200 minutes / 60)
  "6M": 180, // ~1-day intervals (259200 minutes / 1440)
  "1Y": 365, // ~1-day intervals (525600 minutes / 1440)
  "5Y": 260, // ~1-week intervals (2628000 minutes / 10080)
  All: 500, // Reasonable sample of all data
};

const TIME_RANGE_OPTIONS: TimeRange[] = [
  "1D",
  "7D",
  "1M",
  "6M",
  "1Y",
  "5Y",
  "All",
];

type ChartType = "candlestick" | "line";

// Tooltip data interface
interface TooltipData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  x: number;
  y: number;
  visible: boolean;
}

// Floating Tooltip Component
function FloatingTooltip({ data }: { data: TooltipData }) {
  if (!data.visible) return null;

  const formatDate = (timestamp: string) => {
    const date = new Date(parseInt(timestamp) * 1000);
    return date.toLocaleDateString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatNumber = (num: number) =>
    num.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  return (
    <Paper
      shadow="md"
      p="xs"
      radius="md"
      style={{
        position: "absolute",
        left: data.x + 10,
        top: data.y - 10,
        zIndex: 1000,
        backgroundColor: THEME_C_COLORS.core.white,
        border: `1px solid ${THEME_C_COLORS.core.steelGray}`,
        minWidth: "200px",
        pointerEvents: "none",
      }}
    >
      <Text size="xs" fw={600} c={THEME_C_COLORS.core.black} mb={4}>
        {formatDate(data.time)}
      </Text>
      <Group gap="xs" mb={2}>
        <Text size="xs" c={THEME_C_COLORS.core.ironGray}>
          O:
        </Text>
        <Text size="xs" fw={500}>
          ${formatNumber(data.open)}
        </Text>
      </Group>
      <Group gap="xs" mb={2}>
        <Text size="xs" c={THEME_C_COLORS.tartan.greenThread}>
          H:
        </Text>
        <Text size="xs" fw={500}>
          ${formatNumber(data.high)}
        </Text>
      </Group>
      <Group gap="xs" mb={2}>
        <Text size="xs" c={THEME_C_COLORS.core.primaryRed}>
          L:
        </Text>
        <Text size="xs" fw={500}>
          ${formatNumber(data.low)}
        </Text>
      </Group>
      <Group gap="xs" mb={2}>
        <Text size="xs" c={THEME_C_COLORS.core.black}>
          C:
        </Text>
        <Text size="xs" fw={500}>
          ${formatNumber(data.close)}
        </Text>
      </Group>
      <Group gap="xs">
        <Text size="xs" c={THEME_C_COLORS.tartan.tealThread}>
          V:
        </Text>
        <Text size="xs" fw={500}>
          {data.volume.toLocaleString()}
        </Text>
      </Group>
    </Paper>
  );
}

export function TradingViewChart() {
  const [loading, setLoading] = useState<boolean>(false);
  const [availablePairs, setAvailablePairs] = useState<string[]>([]);
  const [selectedPair, setSelectedPair] = useState<string>("BTC-USD");
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>("1M");
  const [chartType, setChartType] = useState<ChartType>("candlestick");
  const [tooltipData, setTooltipData] = useState<TooltipData>({
    time: "",
    open: 0,
    high: 0,
    low: 0,
    close: 0,
    volume: 0,
    x: 0,
    y: 0,
    visible: false,
  });

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);

  // Load available trading pairs on component mount
  useEffect(() => {
    const loadPairs = async () => {
      try {
        const pairs = await DataAPI.getCoinbasePairs();
        setAvailablePairs(pairs);
        if (pairs.length > 0 && !pairs.includes(selectedPair)) {
          setSelectedPair(pairs[0]);
        }
      } catch (error) {
        console.error("Failed to load trading pairs:", error);
        notifications.show({
          title: "Error",
          message: "Failed to load available trading pairs",
          color: "red",
        });
      }
    };

    loadPairs();
  }, []);

  // Load chart data when pair or time range changes
  useEffect(() => {
    if (!selectedPair) return;

    const loadChartData = async () => {
      setLoading(true);
      try {
        const { createChart, CandlestickSeries, LineSeries, HistogramSeries } =
          await import("lightweight-charts");

        // Calculate time range properly
        const endTime = new Date();
        const startTime = new Date();

        switch (selectedTimeRange) {
          case "1D":
            startTime.setDate(endTime.getDate() - 1);
            break;
          case "7D":
            startTime.setDate(endTime.getDate() - 7);
            break;
          case "1M":
            startTime.setMonth(endTime.getMonth() - 1);
            break;
          case "6M":
            startTime.setMonth(endTime.getMonth() - 6);
            break;
          case "1Y":
            startTime.setFullYear(endTime.getFullYear() - 1);
            break;
          case "5Y":
            startTime.setFullYear(endTime.getFullYear() - 5);
            break;
          case "All":
            // For "All", don't set a start time to get all available data
            startTime.setFullYear(2020); // Set to a reasonable start date
            break;
        }

        // Fetch data with appropriate limit for the time range
        const dataLimit = DATA_POINT_LIMITS[selectedTimeRange];
        const queryParams: any = {
          endTime: endTime.toISOString(),
          limit: dataLimit,
        };

        // Only include startTime if not "All" to get maximum available data
        if (selectedTimeRange !== "All") {
          queryParams.startTime = startTime.toISOString();
        }

        const data = await DataAPI.getChartData(selectedPair, queryParams);

        if (!chartContainerRef.current) {
          throw new Error("Chart container not available");
        }

        // Clear existing chart
        if (chartRef.current) {
          chartRef.current.remove();
        }

        // Create new chart
        chartRef.current = createChart(chartContainerRef.current, {
          width: chartContainerRef.current.offsetWidth,
          height: 400,
          layout: {
            background: { color: THEME_C_COLORS.core.white },
            textColor: THEME_C_COLORS.core.black,
          },
          grid: {
            vertLines: { color: THEME_C_COLORS.core.steelGray },
            horzLines: { color: THEME_C_COLORS.core.steelGray },
          },
          crosshair: {
            mode: 1,
          },
          rightPriceScale: {
            borderColor: THEME_C_COLORS.core.steelGray,
          },
          timeScale: {
            borderColor: THEME_C_COLORS.core.steelGray,
            timeVisible: true,
            secondsVisible: false,
            fixLeftEdge: true,
            fixRightEdge: true,
            tickMarkFormatter: (time: any) => {
              // Ensure time is treated as seconds
              const timestamp =
                typeof time === "number" ? time : parseInt(time);
              const date = new Date(timestamp * 1000);

              // Format based on time range
              switch (selectedTimeRange) {
                case "1D":
                  return date.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  });
                case "7D":
                  return date.toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                  });
                case "1M":
                  return date.toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                  });
                case "6M":
                case "1Y":
                  return date.toLocaleDateString([], {
                    month: "short",
                    year: "2-digit",
                  });
                case "5Y":
                case "All":
                  return date.toLocaleDateString([], {
                    year: "numeric",
                  });
                default:
                  return date.toLocaleDateString();
              }
            },
          },
        });

        // Prepare data for lightweight-charts format (convert timestamp to seconds if needed)
        const chartData = data.map((candle) => ({
          time: (candle.time > 1e10
            ? Math.floor(candle.time / 1000)
            : candle.time) as any,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        }));

        const volumeData = data.map((candle) => ({
          time: (candle.time > 1e10
            ? Math.floor(candle.time / 1000)
            : candle.time) as any,
          value: candle.volume,
          color:
            candle.close >= candle.open
              ? THEME_C_COLORS.tartan.greenThread
              : THEME_C_COLORS.core.primaryRed,
        }));

        // Add price series
        if (chartType === "candlestick") {
          seriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
            upColor: THEME_C_COLORS.tartan.greenThread,
            downColor: THEME_C_COLORS.core.primaryRed,
            borderVisible: false,
            wickUpColor: THEME_C_COLORS.tartan.greenThread,
            wickDownColor: THEME_C_COLORS.core.primaryRed,
          });
        } else {
          seriesRef.current = chartRef.current.addSeries(LineSeries, {
            color: THEME_C_COLORS.tartan.tealThread,
            lineWidth: 2,
          });
          // For line chart, use close prices
          const lineData = chartData.map((d) => ({
            time: d.time,
            value: d.close,
          }));
          seriesRef.current.setData(lineData);
        }

        if (chartType === "candlestick") {
          seriesRef.current.setData(chartData);
        }

        // Add volume series
        volumeSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
          color: THEME_C_COLORS.tartan.tealThread,
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
          scaleMargins: {
            top: 0.7,
            bottom: 0,
          },
        });
        volumeSeriesRef.current.setData(volumeData);

        // Add crosshair move handler for tooltip
        chartRef.current.subscribeCrosshairMove((param: any) => {
          if (
            param.point === undefined ||
            !param.time ||
            param.point.x < 0 ||
            param.point.x > chartContainerRef.current!.clientWidth ||
            param.point.y < 0 ||
            param.point.y > chartContainerRef.current!.clientHeight
          ) {
            setTooltipData((prev) => ({ ...prev, visible: false }));
            return;
          }

          const priceData = param.seriesData.get(seriesRef.current);
          const volumeData = param.seriesData.get(volumeSeriesRef.current);

          if (priceData && volumeData) {
            const ohlcData =
              chartType === "candlestick"
                ? priceData
                : {
                    open: priceData.value,
                    high: priceData.value,
                    low: priceData.value,
                    close: priceData.value,
                  };

            setTooltipData({
              time: param.time.toString(),
              open: ohlcData.open,
              high: ohlcData.high,
              low: ohlcData.low,
              close: ohlcData.close,
              volume: volumeData.value,
              x: param.point.x,
              y: param.point.y,
              visible: true,
            });
          }
        });

        // Fit content
        chartRef.current.timeScale().fitContent();
      } catch (error) {
        console.error("Failed to load chart data:", error);
        notifications.show({
          title: "Chart Error",
          message:
            error instanceof Error
              ? error.message
              : "Failed to load chart data",
          color: "red",
        });
      } finally {
        setLoading(false);
      }
    };

    loadChartData();
  }, [selectedPair, selectedTimeRange, chartType]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.offsetWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <Paper shadow="sm" p="lg" radius="md" pos="relative">
      <LoadingOverlay visible={loading} />

      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Title order={3}>
            Price Chart{" "}
            {selectedPair && (
              <Badge variant="light" ml="xs">
                {selectedPair}
              </Badge>
            )}
          </Title>
        </Group>

        <Group gap="md">
          <Select
            label="Trading Pair"
            value={selectedPair}
            onChange={(value) => value && setSelectedPair(value)}
            data={availablePairs.map((pair) => ({ value: pair, label: pair }))}
            searchable
            w={150}
          />

          <Group gap="xs">
            <Text size="sm" fw={500}>
              Time Range:
            </Text>
            {TIME_RANGE_OPTIONS.map((range) => (
              <Button
                key={range}
                variant={selectedTimeRange === range ? "filled" : "outline"}
                size="xs"
                onClick={() => setSelectedTimeRange(range)}
              >
                {TIME_RANGES[range].label}
              </Button>
            ))}
          </Group>

          <Group gap="xs">
            <Text size="sm" fw={500}>
              Chart Type:
            </Text>
            <Button
              variant={chartType === "candlestick" ? "filled" : "outline"}
              size="xs"
              onClick={() => setChartType("candlestick")}
            >
              Candlestick
            </Button>
            <Button
              variant={chartType === "line" ? "filled" : "outline"}
              size="xs"
              onClick={() => setChartType("line")}
            >
              Line
            </Button>
          </Group>
        </Group>

        <div
          ref={chartContainerRef}
          style={{
            width: "100%",
            height: "400px",
            border: `1px solid ${THEME_C_COLORS.core.steelGray}`,
            borderRadius: "8px",
            position: "relative",
          }}
        />

        <FloatingTooltip data={tooltipData} />
      </Stack>
    </Paper>
  );
}
