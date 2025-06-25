import {
  ActionIcon,
  Alert,
  Button,
  Divider,
  Fieldset,
  Grid,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { useForm } from "@mantine/form";
import { useDisclosure } from "@mantine/hooks";
import { IconInfoCircle, IconPlus, IconTrash } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { fetchDateRanges, fetchTradingPairs } from "../api/data";
import { MANTINE_THEME_A_COLORS } from "../theme/theme_a";
import type { BacktestParams, SignalParams } from "../types/backtest";
import { defaultBacktestParams } from "../types/backtest";

interface AssetConfig {
  ticker: string;
  max_position_size_pct?: number;
  min_trade_size_pct?: number;
  min_holding_candle?: number;
  trailing_stop_loss_pct?: number;
  trailing_stop_update_threshold_pct?: number;
  take_profit_pct?: number;
  risk_per_trade_pct?: number;
  sell_fraction?: number;
  cool_down_period?: number;
  strategies?: SignalParams[];
}

interface StrategyConfig {
  type: string;
  parameters: Record<string, number | string | null>;
}

interface BacktestFormProps {
  onSubmit: (params: BacktestParams) => void;
  loading?: boolean;
}

// Define a separate type for form state
interface BacktestFormState extends Omit<BacktestParams, "start" | "end"> {
  start: Date | null;
  end: Date | null;
}

export function BacktestForm({ onSubmit, loading = false }: BacktestFormProps) {
  const [opened, { open, close }] = useDisclosure(false);
  const [strategyOpened, { open: openStrategy, close: closeStrategy }] =
    useDisclosure(false);
  const [detailsOpened, { open: openDetails, close: closeDetails }] =
    useDisclosure(false);
  const [assets, setAssets] = useState<AssetConfig[]>([]);
  const [editingAsset, setEditingAsset] = useState<AssetConfig | null>(null);
  const [viewingAsset, setViewingAsset] = useState<AssetConfig | null>(null);

  // New state for API data
  const [tradingPairs, setTradingPairs] = useState<string[]>([]);
  const [dateRanges, setDateRanges] = useState<
    Record<string, [number, number]>
  >({});
  const [earliestDate, setEarliestDate] = useState<Date | null>(null);
  const [latestDate, setLatestDate] = useState<Date | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);

  // Ref to track the last calculated date range to prevent infinite loops
  const lastDateRangeRef = useRef<{ start: string; end: string } | null>(null);

  const form = useForm<BacktestFormState>({
    initialValues: {
      ...defaultBacktestParams,
      start: null,
      end: null,
    },
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
        capital_growth_pct: (value) =>
          value < 0 ? "Capital growth percentage cannot be negative" : null,
        capital_growth_amount: (value) =>
          value < 0 ? "Capital growth amount cannot be negative" : null,
      },
      portfolio_constraints_params: {
        rebalance_threshold_pct: (value) =>
          value < 0 ? "Rebalance threshold cannot be negative" : null,
        min_cash_pct: (value) =>
          value < 0 || value > 100
            ? "Min cash percentage must be between 0 and 100"
            : null,
        max_drawdown_pct: (value) =>
          value < 0 || value > 100
            ? "Max drawdown percentage must be between 0 and 100"
            : null,
      },
    },
  });

  // Fetch data on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoadingData(true);
        const [pairs, ranges] = await Promise.all([
          fetchTradingPairs(),
          fetchDateRanges(),
        ]);

        setTradingPairs(pairs);
        setDateRanges(ranges);

        // Calculate earliest and latest dates from all ranges
        const allStartDates: number[] = [];
        const allEndDates: number[] = [];

        Object.values(ranges).forEach(([start, end]) => {
          allStartDates.push(start);
          allEndDates.push(end);
        });

        if (allStartDates.length > 0 && allEndDates.length > 0) {
          const earliestTimestamp = Math.min(...allStartDates);
          const latestTimestamp = Math.max(...allEndDates);

          const earliest = new Date(earliestTimestamp * 1000);
          const latest = new Date(latestTimestamp * 1000);

          setEarliestDate(earliest);
          setLatestDate(latest);

          // Set default dates in the form
          form.setFieldValue("start", earliest);
          form.setFieldValue("end", latest);
        }
      } catch (error) {
        console.error("Failed to fetch trading data:", error);
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchData();
  }, []);

  // Update form values when valid date range changes due to asset selection
  useEffect(() => {
    // Only update if data is loaded and not currently loading
    if (isLoadingData || Object.keys(dateRanges).length === 0) {
      return;
    }

    const { validMinDate, validMaxDate } = calculateValidDateRange();

    if (validMinDate && validMaxDate) {
      const newStartDate = validMinDate.toISOString().split("T")[0];
      const newEndDate = validMaxDate.toISOString().split("T")[0];

      // Check if this is actually a different date range than what we last set
      const lastRange = lastDateRangeRef.current;
      if (
        !lastRange ||
        lastRange.start !== newStartDate ||
        lastRange.end !== newEndDate
      ) {
        form.setFieldValue("start", validMinDate);
        form.setFieldValue("end", validMaxDate);

        // Update the ref to track what we just set
        lastDateRangeRef.current = { start: newStartDate, end: newEndDate };
      }
    }
  }, [
    assets.length,
    JSON.stringify(assets.map((a) => a.ticker)),
    isLoadingData,
  ]);

  const calculateValidDateRange = () => {
    if (assets.length === 0) {
      return { validMinDate: earliestDate, validMaxDate: latestDate };
    }

    let latestStartDate = 0; // Latest start date among selected assets
    let earliestEndDate = Number.MAX_SAFE_INTEGER; // Earliest end date among selected assets

    for (const asset of assets) {
      const range = dateRanges[asset.ticker];
      if (range) {
        const [startTs, endTs] = range;
        latestStartDate = Math.max(latestStartDate, startTs);
        earliestEndDate = Math.min(earliestEndDate, endTs);
      }
    }

    // Use the latest start date directly (backend already adds buffer)
    const validMinDate =
      latestStartDate > 0 ? new Date(latestStartDate * 1000) : earliestDate;
    const validMaxDate =
      earliestEndDate < Number.MAX_SAFE_INTEGER
        ? new Date(earliestEndDate * 1000)
        : latestDate;

    return { validMinDate, validMaxDate };
  };

  const assetForm = useForm<AssetConfig>({
    initialValues: {
      ticker: "",
      max_position_size_pct: 25,
      min_trade_size_pct: 1,
      min_holding_candle: 5,
      cool_down_period: 5,
      trailing_stop_loss_pct: 5,
      trailing_stop_update_threshold_pct: 1,
      take_profit_pct: 10,
      risk_per_trade_pct: 2,
      sell_fraction: 0.5,
      strategies: [],
    },
    validate: {
      ticker: (value) =>
        value.length < 1 ? "Asset selection is required" : null,
      strategies: (value) =>
        !value || value.length === 0
          ? "At least one strategy is required"
          : null,
    },
  });

  const strategyForm = useForm<StrategyConfig>({
    initialValues: {
      type: "",
      parameters: {},
    },
    validate: {
      type: (value) => (value.length < 1 ? "Strategy type is required" : null),
    },
  });

  const handleSubmit = (values: BacktestFormState) => {
    // Convert start and end to proper Date objects if they're strings
    let startDate: Date | null = values.start;
    let endDate: Date | null = values.end;

    if (typeof values.start === "string") {
      startDate = new Date(values.start);
    }

    if (typeof values.end === "string") {
      endDate = new Date(values.end);
    }

    const submitValues: BacktestParams = {
      ...values,
      tickers: assets.map((asset) => asset.ticker),
      strategies: assets.map((asset) => asset.strategies || []),
      portfolio_params: {
        ...values.portfolio_params,
        capital_growth_pct: values.portfolio_params.capital_growth_pct / 100,
      },
      portfolio_constraints_params: {
        ...values.portfolio_constraints_params,
        rebalance_threshold_pct:
          values.portfolio_constraints_params.rebalance_threshold_pct / 100,
        min_cash_pct: values.portfolio_constraints_params.min_cash_pct / 100,
        max_drawdown_pct:
          values.portfolio_constraints_params.max_drawdown_pct / 100,
      },
      position_constraints_params: assets.map((asset) => ({
        max_position_size_pct: (asset.max_position_size_pct || 0) / 100,
        min_trade_size_pct: (asset.min_trade_size_pct || 0) / 100,
        min_holding_candle: asset.min_holding_candle || 0,
        cool_down_period: asset.cool_down_period || 0,
        trailing_stop_loss_pct: (asset.trailing_stop_loss_pct || 0) / 100,
        trailing_stop_update_threshold_pct:
          (asset.trailing_stop_update_threshold_pct || 0) / 100,
        take_profit_pct: (asset.take_profit_pct || 0) / 100,
        risk_per_trade_pct: (asset.risk_per_trade_pct || 0) / 100,
        sell_fraction: asset.sell_fraction || 0,
      })),
      start: startDate
        ? new Date(
            startDate.getFullYear(),
            startDate.getMonth(),
            startDate.getDate(),
            0,
            0,
            0,
            0
          ).toISOString()
        : "",
      end: endDate
        ? new Date(
            endDate.getFullYear(),
            endDate.getMonth(),
            endDate.getDate(),
            23,
            59,
            59,
            999
          ).toISOString()
        : "",
    };

    onSubmit(submitValues);
  };

  const handleRestoreDefaults = () => {
    // Generate a new UUID for the fresh backtest
    const newDefaults = {
      ...defaultBacktestParams,
      backtest_id: crypto.randomUUID(), // Generate new UUID
      start: earliestDate,
      end: latestDate,
    };
    form.setValues(newDefaults);

    // Also reset the assets state
    setAssets([]);
  };

  const handleAddAsset = () => {
    setEditingAsset(null);
    assetForm.reset();
    open();
  };

  const handleEditAsset = (asset: AssetConfig) => {
    setEditingAsset(asset);
    assetForm.setValues(asset);
    open();
  };

  const handleSaveAsset = (values: AssetConfig) => {
    if (editingAsset) {
      // Edit existing asset
      setAssets((prev) =>
        prev.map((a) => (a.ticker === editingAsset.ticker ? values : a))
      );
    } else {
      // Add new asset
      if (assets.some((a) => a.ticker === values.ticker)) {
        assetForm.setFieldError("ticker", "This asset is already added");
        return;
      }
      setAssets((prev) => [...prev, values]);
    }
    close();
  };

  const handleRemoveAsset = (ticker: string) => {
    setAssets((prev) => prev.filter((a) => a.ticker !== ticker));
  };

  const handleViewAssetDetails = (asset: AssetConfig) => {
    setViewingAsset(asset);
    openDetails();
  };

  // Create asset options from trading pairs
  const allAssets = tradingPairs.map((pair) => ({
    value: pair,
    label: pair,
  }));

  // Filter out already selected assets, but include the currently editing asset
  const availableAssets = allAssets.filter((asset) => {
    const isAlreadySelected = assets.some(
      (selectedAsset) => selectedAsset.ticker === asset.value
    );
    const isCurrentlyEditing = editingAsset?.ticker === asset.value;
    return !isAlreadySelected || isCurrentlyEditing;
  });

  const allStrategies = [
    { value: "EmaRsiMacd", label: "EMA RSI MACD Strategy" },
    { value: "BbRsiOversold", label: "Bollinger Bands RSI Oversold" },
    { value: "BbRsiOverbought", label: "Bollinger Bands RSI Overbought" },
    { value: "PatternRsiMacd", label: "Pattern RSI MACD" },
    { value: "TripleEmaPatternMacdRsi", label: "Triple EMA Pattern MACD RSI" },
    { value: "BbSqueezeBreakout", label: "Bollinger Bands Squeeze Breakout" },
    { value: "RsiOversoldReversal", label: "RSI Oversold Reversal" },
    { value: "SupportBounce", label: "Support Bounce" },
    { value: "UptrendPattern", label: "Uptrend Pattern" },
    { value: "StochOversold", label: "Stochastic Oversold" },
  ];

  // Filter out already selected strategies for the current asset
  const availableStrategies = allStrategies.filter((strategy) => {
    const currentStrategies = assetForm.values.strategies || [];
    const isAlreadySelected = currentStrategies.some((selectedStrategy) => {
      // Check if this strategy type is already selected
      return Object.keys(selectedStrategy)[0] === strategy.value;
    });
    return !isAlreadySelected;
  });

  const getStrategyParameterFields = (strategyType: string) => {
    switch (strategyType) {
      case "EmaRsiMacd":
        return [
          {
            key: "ema_fast",
            label: "EMA Fast Period",
            defaultValue: 12,
            description: "Fast EMA period",
          },
          {
            key: "ema_medium",
            label: "EMA Medium Period",
            defaultValue: 26,
            description: "Medium EMA period",
          },
          {
            key: "ema_slow",
            label: "EMA Slow Period",
            defaultValue: 50,
            description: "Slow EMA period",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
          {
            key: "macd_fast",
            label: "MACD Fast",
            defaultValue: 12,
            description: "MACD fast period",
          },
          {
            key: "macd_slow",
            label: "MACD Slow",
            defaultValue: 26,
            description: "MACD slow period",
          },
          {
            key: "macd_signal",
            label: "MACD Signal",
            defaultValue: 9,
            description: "MACD signal period",
          },
        ];
      case "BbRsiOversold":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "BB_RSI_Oversold",
            description: "Strategy identifier",
          },
          {
            key: "std_dev",
            label: "Standard Deviation",
            defaultValue: 2.0,
            description: "Bollinger Bands standard deviation",
          },
          {
            key: "initial_close",
            label: "Initial Close Price",
            defaultValue: 50000,
            description: "Starting price for calculations",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
        ];
      case "BbRsiOverbought":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "BB_RSI_Overbought",
            description: "Strategy identifier",
          },
          {
            key: "std_dev",
            label: "Standard Deviation",
            defaultValue: 2.0,
            description: "Bollinger Bands standard deviation",
          },
          {
            key: "initial_close",
            label: "Initial Close Price",
            defaultValue: 50000,
            description: "Starting price for calculations",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
        ];
      case "PatternRsiMacd":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "Pattern_RSI_MACD",
            description: "Strategy identifier",
          },
          {
            key: "resistance_threshold",
            label: "Resistance Threshold",
            defaultValue: 0.02,
            description: "Resistance level threshold",
          },
          {
            key: "support_threshold",
            label: "Support Threshold",
            defaultValue: 0.02,
            description: "Support level threshold",
          },
          {
            key: "initial_high",
            label: "Initial High",
            defaultValue: 55000,
            description: "Starting high price",
          },
          {
            key: "initial_low",
            label: "Initial Low",
            defaultValue: 45000,
            description: "Starting low price",
          },
          {
            key: "initial_close",
            label: "Initial Close",
            defaultValue: 50000,
            description: "Starting close price",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
          {
            key: "macd_fast",
            label: "MACD Fast",
            defaultValue: 12,
            description: "MACD fast period",
          },
          {
            key: "macd_slow",
            label: "MACD Slow",
            defaultValue: 26,
            description: "MACD slow period",
          },
          {
            key: "macd_signal",
            label: "MACD Signal",
            defaultValue: 9,
            description: "MACD signal period",
          },
        ];
      case "TripleEmaPatternMacdRsi":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "Triple_EMA_Pattern",
            description: "Strategy identifier",
          },
          {
            key: "ema_fast",
            label: "EMA Fast",
            defaultValue: 9,
            description: "Fast EMA period",
          },
          {
            key: "ema_medium",
            label: "EMA Medium",
            defaultValue: 21,
            description: "Medium EMA period",
          },
          {
            key: "ema_slow",
            label: "EMA Slow",
            defaultValue: 55,
            description: "Slow EMA period",
          },
          {
            key: "resistance_threshold",
            label: "Resistance Threshold",
            defaultValue: 0.02,
            description: "Resistance level threshold",
          },
          {
            key: "support_threshold",
            label: "Support Threshold",
            defaultValue: 0.02,
            description: "Support level threshold",
          },
          {
            key: "initial_high",
            label: "Initial High",
            defaultValue: 55000,
            description: "Starting high price",
          },
          {
            key: "initial_low",
            label: "Initial Low",
            defaultValue: 45000,
            description: "Starting low price",
          },
          {
            key: "initial_close",
            label: "Initial Close",
            defaultValue: 50000,
            description: "Starting close price",
          },
          {
            key: "macd_fast",
            label: "MACD Fast",
            defaultValue: 12,
            description: "MACD fast period",
          },
          {
            key: "macd_slow",
            label: "MACD Slow",
            defaultValue: 26,
            description: "MACD slow period",
          },
          {
            key: "macd_signal",
            label: "MACD Signal",
            defaultValue: 9,
            description: "MACD signal period",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 75,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 25,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 35,
            description: "RSI bullish divergence threshold",
          },
        ];
      case "BbSqueezeBreakout":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "BB_Squeeze_Breakout",
            description: "Strategy identifier",
          },
          {
            key: "std_dev",
            label: "Standard Deviation",
            defaultValue: 2.0,
            description: "Bollinger Bands standard deviation",
          },
          {
            key: "macd_fast",
            label: "MACD Fast",
            defaultValue: 12,
            description: "MACD fast period",
          },
          {
            key: "macd_slow",
            label: "MACD Slow",
            defaultValue: 26,
            description: "MACD slow period",
          },
          {
            key: "macd_signal",
            label: "MACD Signal",
            defaultValue: 9,
            description: "MACD signal period",
          },
        ];
      case "RsiOversoldReversal":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "RSI_Oversold_Reversal",
            description: "Strategy identifier",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
          {
            key: "ema_fast",
            label: "EMA Fast",
            defaultValue: 12,
            description: "Fast EMA period",
          },
          {
            key: "ema_medium",
            label: "EMA Medium",
            defaultValue: 26,
            description: "Medium EMA period",
          },
          {
            key: "ema_slow",
            label: "EMA Slow",
            defaultValue: 50,
            description: "Slow EMA period",
          },
        ];
      case "SupportBounce":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "Support_Bounce",
            description: "Strategy identifier",
          },
          {
            key: "resistance_threshold",
            label: "Resistance Threshold",
            defaultValue: 0.02,
            description: "Resistance level threshold",
          },
          {
            key: "support_threshold",
            label: "Support Threshold",
            defaultValue: 0.02,
            description: "Support level threshold",
          },
          {
            key: "macd_fast",
            label: "MACD Fast",
            defaultValue: 12,
            description: "MACD fast period",
          },
          {
            key: "macd_slow",
            label: "MACD Slow",
            defaultValue: 26,
            description: "MACD slow period",
          },
          {
            key: "macd_signal",
            label: "MACD Signal",
            defaultValue: 9,
            description: "MACD signal period",
          },
        ];
      case "UptrendPattern":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "Uptrend_Pattern",
            description: "Strategy identifier",
          },
          {
            key: "ema_fast",
            label: "EMA Fast",
            defaultValue: 12,
            description: "Fast EMA period",
          },
          {
            key: "ema_medium",
            label: "EMA Medium",
            defaultValue: 26,
            description: "Medium EMA period",
          },
          {
            key: "ema_slow",
            label: "EMA Slow",
            defaultValue: 50,
            description: "Slow EMA period",
          },
          {
            key: "resistance_threshold",
            label: "Resistance Threshold",
            defaultValue: 0.02,
            description: "Resistance level threshold",
          },
          {
            key: "support_threshold",
            label: "Support Threshold",
            defaultValue: 0.02,
            description: "Support level threshold",
          },
          {
            key: "rsi_period",
            label: "RSI Period",
            defaultValue: 14,
            description: "RSI calculation period",
          },
          {
            key: "rsi_ob",
            label: "RSI Overbought",
            defaultValue: 70,
            description: "RSI overbought threshold",
          },
          {
            key: "rsi_os",
            label: "RSI Oversold",
            defaultValue: 30,
            description: "RSI oversold threshold",
          },
          {
            key: "rsi_bull_div",
            label: "RSI Bull Divergence",
            defaultValue: 40,
            description: "RSI bullish divergence threshold",
          },
        ];
      case "StochOversold":
        return [
          {
            key: "name",
            label: "Strategy Name",
            defaultValue: "Stoch_Oversold",
            description: "Strategy identifier",
          },
          {
            key: "ema_fast_period",
            label: "EMA Fast Period",
            defaultValue: 12,
            description: "Fast EMA period",
          },
          {
            key: "ema_slow_period",
            label: "EMA Slow Period",
            defaultValue: 26,
            description: "Slow EMA period",
          },
          {
            key: "oversold",
            label: "Oversold Threshold",
            defaultValue: 20,
            description: "Stochastic oversold threshold",
          },
        ];
      default:
        return [];
    }
  };

  // Initialize strategy parameters when strategy type changes
  const handleStrategyTypeChange = (strategyType: string) => {
    const fields = getStrategyParameterFields(strategyType);
    const defaultParams: Record<string, number | string | null> = {};
    fields.forEach((field) => {
      // Skip initial price fields - they'll be handled automatically by the backend
      if (!field.key.startsWith("initial_")) {
        defaultParams[field.key] = field.defaultValue;
      }
    });
    // Set initial price fields to null so backend can use current price
    defaultParams["initial_close"] = null;
    defaultParams["initial_high"] = null;
    defaultParams["initial_low"] = null;

    strategyForm.setFieldValue("type", strategyType);
    strategyForm.setFieldValue("parameters", defaultParams);
  };

  const handleAddStrategy = () => {
    strategyForm.reset();
    openStrategy();
  };

  const handleSaveStrategy = (values: StrategyConfig) => {
    // Convert strategy config to SignalParams format
    const signalParams: SignalParams = {
      [values.type]: values.parameters,
    } as SignalParams;

    const updatedStrategies = [
      ...(assetForm.values.strategies || []),
      signalParams,
    ];
    assetForm.setFieldValue("strategies", updatedStrategies);
    closeStrategy();
  };

  const handleRemoveStrategy = (index: number) => {
    const updatedStrategies = (assetForm.values.strategies || []).filter(
      (_, i) => i !== index
    );
    assetForm.setFieldValue("strategies", updatedStrategies);
  };

  const { validMinDate, validMaxDate } = calculateValidDateRange();

  return (
    <>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="lg">
          <Alert
            icon={<IconInfoCircle size={16} />}
            title="Quick Start"
            color="blue"
          >
            <Text size="sm">say something imgiving up</Text>
          </Alert>

          <Fieldset
            legend={
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                Basic Configuration
              </Text>
            }
          >
            <Stack gap="md">
              <Text size="sm" c="dimmed">
                <Text component="span" fw={500}>
                  Backtest ID:
                </Text>{" "}
                {form.values.backtest_id}
              </Text>
              <Grid>
                <Grid.Col span={6}>
                  <TextInput
                    label="Strategy Name"
                    placeholder="Enter strategy name"
                    required
                    {...form.getInputProps("strategy_name")}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Portfolio Name"
                    placeholder="Enter portfolio name"
                    required
                    {...form.getInputProps("portfolio_name")}
                  />
                </Grid.Col>
              </Grid>
            </Stack>
          </Fieldset>

          <Fieldset
            legend={
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                Assets Configuration
              </Text>
            }
          >
            <Stack gap="md">
              <Group justify="space-between">
                <Button
                  fullWidth
                  leftSection={<IconPlus size={16} />}
                  onClick={handleAddAsset}
                  variant="light"
                >
                  Add Asset
                </Button>
              </Group>

              {assets.length > 0 ? (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Asset</Table.Th>
                      <Table.Th>Strategies</Table.Th>
                      <Table.Th style={{ textAlign: "right" }}>
                        Actions
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {assets.map((asset) => (
                      <Table.Tr key={asset.ticker}>
                        <Table.Td>
                          <Text size="sm">{asset.ticker}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">
                            {(asset.strategies || []).length}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs" justify="flex-end">
                            <Button
                              size="xs"
                              variant="light"
                              onClick={() => handleViewAssetDetails(asset)}
                            >
                              View Details
                            </Button>
                            <Button
                              size="xs"
                              variant="light"
                              onClick={() => handleEditAsset(asset)}
                            >
                              Edit
                            </Button>
                            <ActionIcon
                              size="sm"
                              color="red"
                              variant="light"
                              onClick={() => handleRemoveAsset(asset.ticker)}
                            >
                              <IconTrash size={14} />
                            </ActionIcon>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              ) : (
                <Text size="sm" c="dimmed" ta="center" py="xl">
                  Add at least one asset to get started.
                </Text>
              )}
            </Stack>
          </Fieldset>

          <Fieldset
            legend={
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                Execution Parameters
              </Text>
            }
          >
            {/* Show trading pair date ranges */}
            {assets.length > 0 && (
              <Stack gap="xs" mb="md">
                <Text size="xs" fw={700} c="dimmed">
                  Data Availability:
                </Text>
                {assets.map((asset) => {
                  const range = dateRanges[asset.ticker];
                  if (range) {
                    const startDate = new Date(range[0] * 1000)
                      .toISOString()
                      .slice(0, 10)
                      .replace(/-/g, "-");
                    const endDate = new Date(range[1] * 1000)
                      .toISOString()
                      .slice(0, 10)
                      .replace(/-/g, "-");
                    return (
                      <Text key={asset.ticker} size="xs" c="dimmed">
                        {asset.ticker}: {startDate} | {endDate}
                      </Text>
                    );
                  }
                  return null;
                })}

                {/* Show valid date range */}
                {validMinDate && validMaxDate && (
                  <Text size="xs" fw={700} c="blue">
                    Valid Range: {validMinDate.toISOString().slice(0, 10)} |{" "}
                    {validMaxDate.toISOString().slice(0, 10)}
                  </Text>
                )}
              </Stack>
            )}
            <Grid>
              <Grid.Col span={6}>
                <DateInput
                  label="Start Date"
                  placeholder="YYYY-MM-DD"
                  required
                  clearable
                  valueFormat="YYYY-MM-DD"
                  minDate={validMinDate || undefined}
                  maxDate={validMaxDate || undefined}
                  value={form.values.start}
                  onChange={(value) => {
                    if (
                      value &&
                      typeof value === "object" &&
                      "getTime" in value
                    ) {
                      form.setFieldValue("start", value as Date);
                    } else if (typeof value === "string" && value) {
                      const parsed = new Date(value);
                      if (!isNaN(parsed.getTime())) {
                        form.setFieldValue("start", parsed);
                      }
                    } else {
                      form.setFieldValue("start", null);
                    }
                  }}
                  onBlur={(event) => {
                    const value = event.target.value;
                    if (
                      value &&
                      value !== form.values.start?.toISOString().split("T")[0]
                    ) {
                      const parsed = new Date(value);
                      if (!isNaN(parsed.getTime())) {
                        form.setFieldValue("start", parsed);
                      }
                    }
                  }}
                  error={form.errors.start}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <DateInput
                  label="End Date"
                  placeholder="YYYY-MM-DD"
                  required
                  clearable
                  valueFormat="YYYY-MM-DD"
                  minDate={validMinDate || undefined}
                  maxDate={validMaxDate || undefined}
                  value={form.values.end}
                  onChange={(value) => {
                    if (
                      value &&
                      typeof value === "object" &&
                      "getTime" in value
                    ) {
                      form.setFieldValue("end", value as Date);
                    } else if (typeof value === "string" && value) {
                      const parsed = new Date(value);
                      if (!isNaN(parsed.getTime())) {
                        form.setFieldValue("end", parsed);
                      }
                    } else {
                      form.setFieldValue("end", null);
                    }
                  }}
                  onBlur={(event) => {
                    const value = event.target.value;
                    if (
                      value &&
                      value !== form.values.end?.toISOString().split("T")[0]
                    ) {
                      const parsed = new Date(value);
                      if (!isNaN(parsed.getTime())) {
                        form.setFieldValue("end", parsed);
                      }
                    }
                  }}
                  error={form.errors.end}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <NumberInput
                  label="Warm Up Period"
                  placeholder="Enter warm up period"
                  min={0}
                  description="Number of periods to warm up indicators"
                  {...form.getInputProps("warm_up_period")}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <NumberInput
                  label="Cadence (minutes)"
                  placeholder="Enter cadence in minutes"
                  min={1}
                  step={5}
                  description="Time interval between sampling & evaluations"
                  {...form.getInputProps("cadence")}
                />
              </Grid.Col>
            </Grid>
          </Fieldset>

          <Fieldset
            legend={
              <Text fw={600} c={MANTINE_THEME_A_COLORS.teal}>
                Portfolio Parameters
              </Text>
            }
          >
            <Text size="sm" c="dimmed" mb="md">
              Capital growth percentage and amount are mutually exclusive.
            </Text>
            <Grid>
              <Grid.Col span={6}>
                <NumberInput
                  label="Initial Cash ($)"
                  placeholder="Enter initial cash amount"
                  min={0}
                  step={1000}
                  thousandSeparator
                  required
                  {...form.getInputProps("portfolio_params.initial_cash")}
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
              <Grid.Col span={6}>
                <NumberInput
                  label="Capital Growth (%)"
                  placeholder="Enter capital growth percentage"
                  description="% of portfolio equity (cash + mv)"
                  min={0}
                  max={100}
                  step={0.01}
                  suffix="%"
                  value={form.values.portfolio_params.capital_growth_pct}
                  onChange={(value) => {
                    const numValue =
                      typeof value === "string"
                        ? parseFloat(value) || 0
                        : value || 0;
                    form.setFieldValue(
                      "portfolio_params.capital_growth_pct",
                      numValue
                    );
                    if (numValue > 0) {
                      form.setFieldValue(
                        "portfolio_params.capital_growth_amount",
                        0
                      );
                    }
                  }}
                  error={form.errors["portfolio_params.capital_growth_pct"]}
                />
              </Grid.Col>
              <Grid.Col span={6}>
                <NumberInput
                  label="Capital Growth Amount ($)"
                  placeholder="Enter capital growth amount"
                  description="Distributed at the END of frequency period"
                  min={0}
                  step={1000}
                  thousandSeparator
                  value={form.values.portfolio_params.capital_growth_amount}
                  onChange={(value) => {
                    const numValue =
                      typeof value === "string"
                        ? parseFloat(value) || 0
                        : value || 0;
                    form.setFieldValue(
                      "portfolio_params.capital_growth_amount",
                      numValue
                    );
                    if (numValue > 0) {
                      form.setFieldValue(
                        "portfolio_params.capital_growth_pct",
                        0
                      );
                    }
                  }}
                  error={form.errors["portfolio_params.capital_growth_amount"]}
                />
              </Grid.Col>
              <Grid.Col span={4}>
                <NumberInput
                  label="Rebalance Threshold (%)"
                  placeholder="Enter rebalance threshold"
                  description="% of portfolio equity"
                  min={0}
                  step={0.01}
                  suffix="%"
                  {...form.getInputProps(
                    "portfolio_constraints_params.rebalance_threshold_pct"
                  )}
                />
              </Grid.Col>
              <Grid.Col span={4}>
                <NumberInput
                  label="Min Cash (%)"
                  placeholder="Enter minimum cash percentage"
                  description="% cash to hold"
                  min={0}
                  max={100}
                  step={0.01}
                  suffix="%"
                  {...form.getInputProps(
                    "portfolio_constraints_params.min_cash_pct"
                  )}
                />
              </Grid.Col>
              <Grid.Col span={4}>
                <NumberInput
                  label="Max Drawdown (%)"
                  placeholder="Enter max drawdown percentage"
                  description="% from peak equity"
                  min={0}
                  max={100}
                  step={0.01}
                  suffix="%"
                  {...form.getInputProps(
                    "portfolio_constraints_params.max_drawdown_pct"
                  )}
                />
              </Grid.Col>
            </Grid>
          </Fieldset>

          <Divider />

          <Group justify="flex-end" gap="sm">
            <Button
              variant="outline"
              onClick={handleRestoreDefaults}
              color="gray"
            >
              Restore to Default
            </Button>
            <Button
              type="submit"
              loading={loading}
              size="md"
              color="yellow"
              disabled={assets.length === 0}
            >
              Run Backtest
            </Button>
          </Group>
        </Stack>
      </form>

      <Modal
        opened={opened}
        onClose={close}
        title={editingAsset ? "Edit Asset" : "Add Asset"}
        size="lg"
      >
        <form onSubmit={assetForm.onSubmit(handleSaveAsset)}>
          <Stack gap="md">
            <Select
              label="Asset"
              placeholder="Select an asset to trade"
              required
              data={availableAssets}
              disabled={!!editingAsset}
              {...assetForm.getInputProps("ticker")}
            />

            <Fieldset
              legend={
                <Text fw={600} c={MANTINE_THEME_A_COLORS.darkestGold} size="sm">
                  Buy Constraints
                </Text>
              }
            >
              <Grid>
                <Grid.Col span={6}>
                  <NumberInput
                    label="Max Position Size (%)"
                    description="% of portfolio equity"
                    placeholder="Maximum position size"
                    min={0}
                    max={100}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.max_position_size_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "max_position_size_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.max_position_size_pct}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <NumberInput
                    label="Min Trade Size (%)"
                    description="% of portfolio equity"
                    placeholder="Minimum trade size"
                    min={0}
                    max={100}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.min_trade_size_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "min_trade_size_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.min_trade_size_pct}
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <NumberInput
                    label="Risk Per Trade (%)"
                    description="Max risk per trade (% of portfolio equity)"
                    placeholder="Risk per trade"
                    min={0}
                    max={100}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.risk_per_trade_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "risk_per_trade_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.risk_per_trade_pct}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <NumberInput
                    label="Min Holding Period"
                    description="multiple of cadence"
                    placeholder="Minimum holding period"
                    min={0}
                    value={assetForm.values.min_holding_candle}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "min_holding_candle",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.min_holding_candle}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <NumberInput
                    label="Cool Down Period"
                    description="min period after a negative exit"
                    placeholder="Cool down period"
                    min={0}
                    value={assetForm.values.cool_down_period}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "cool_down_period",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.cool_down_period}
                  />
                </Grid.Col>
              </Grid>
            </Fieldset>

            <Fieldset
              legend={
                <Text fw={600} c={MANTINE_THEME_A_COLORS.darkestGold} size="sm">
                  Risk Constraints
                </Text>
              }
            >
              <Grid>
                <Grid.Col span={4}>
                  <NumberInput
                    label="Trailing Stop Loss (%)"
                    description="% of high-water mark"
                    placeholder="Trailing stop loss"
                    min={0}
                    max={100}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.trailing_stop_loss_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "trailing_stop_loss_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.trailing_stop_loss_pct}
                  />
                </Grid.Col>
                <Grid.Col span={4}>
                  <NumberInput
                    label="TSL Trigger %"
                    description="% above high-water mark"
                    placeholder="TSL update threshold"
                    min={0}
                    max={100}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.trailing_stop_update_threshold_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "trailing_stop_update_threshold_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.trailing_stop_update_threshold_pct}
                  />
                </Grid.Col>
                <Grid.Col span={4}>
                  <NumberInput
                    label="Take Profit (%)"
                    description="% above avg. entry price"
                    placeholder="Take profit percentage"
                    min={0}
                    step={0.01}
                    suffix="%"
                    value={assetForm.values.take_profit_pct}
                    onChange={(value) =>
                      assetForm.setFieldValue(
                        "take_profit_pct",
                        typeof value === "string"
                          ? parseFloat(value) || 0
                          : value || 0
                      )
                    }
                    error={assetForm.errors.take_profit_pct}
                  />
                </Grid.Col>
              </Grid>
            </Fieldset>

            <Fieldset
              legend={
                <Text fw={600} c={MANTINE_THEME_A_COLORS.darkestGold} size="sm">
                  Sell Constraints
                </Text>
              }
            >
              <NumberInput
                label="Sell Fraction"
                description="% of position to sell on signal driven sell"
                placeholder="Sell fraction"
                min={0}
                max={1}
                step={0.01}
                value={assetForm.values.sell_fraction}
                onChange={(value) =>
                  assetForm.setFieldValue(
                    "sell_fraction",
                    typeof value === "string"
                      ? parseFloat(value) || 0
                      : value || 0
                  )
                }
                error={assetForm.errors.sell_fraction}
              />
            </Fieldset>

            <Fieldset
              legend={
                <Text fw={600} c={MANTINE_THEME_A_COLORS.darkestGold} size="sm">
                  Strategies
                </Text>
              }
            >
              <Stack gap="md">
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    A strategy is a predefined set of rules that acts on
                    multiple indicators. Be mindful not to assign too many
                    strategies to a single asset to avoid signal overload.
                  </Text>
                  <Button
                    fullWidth
                    leftSection={<IconPlus size={16} />}
                    onClick={handleAddStrategy}
                    variant="light"
                    color="violet"
                  >
                    Add Strategy
                  </Button>
                </Group>

                {(assetForm.values.strategies || []).length > 0 ? (
                  <Table>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Strategy Name</Table.Th>
                        <Table.Th style={{ textAlign: "right" }}>
                          Actions
                        </Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {(assetForm.values.strategies || []).map(
                        (strategy, index) => {
                          const strategyType = Object.keys(strategy)[0];
                          return (
                            <Table.Tr key={index}>
                              <Table.Td>
                                <Text size="sm">{strategyType}</Text>
                              </Table.Td>
                              <Table.Td>
                                <Group justify="flex-end">
                                  <ActionIcon
                                    size="sm"
                                    color="red"
                                    variant="light"
                                    onClick={() => handleRemoveStrategy(index)}
                                  >
                                    <IconTrash size={14} />
                                  </ActionIcon>
                                </Group>
                              </Table.Td>
                            </Table.Tr>
                          );
                        }
                      )}
                    </Table.Tbody>
                  </Table>
                ) : (
                  <Text size="sm" c="dimmed" ta="center" py="sm">
                    Add at least one strategy to get started.
                  </Text>
                )}
              </Stack>
              {assetForm.errors.strategies && (
                <Text size="sm" c="red" mt="xs">
                  {assetForm.errors.strategies}
                </Text>
              )}
            </Fieldset>

            <Group justify="flex-end" gap="sm">
              <Button variant="outline" onClick={close}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  !assetForm.values.ticker ||
                  !assetForm.values.strategies ||
                  assetForm.values.strategies.length === 0
                }
              >
                {editingAsset ? "Save Asset" : "Add Asset"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={strategyOpened}
        onClose={closeStrategy}
        title="Add Strategy"
        size="lg"
      >
        <form onSubmit={strategyForm.onSubmit(handleSaveStrategy)}>
          <Stack gap="md">
            <Select
              label="Strategy Type"
              placeholder="Select a strategy type"
              required
              data={availableStrategies}
              onChange={(value) => {
                if (value) {
                  handleStrategyTypeChange(value);
                }
              }}
              value={strategyForm.values.type}
            />

            {strategyForm.values.type && (
              <Fieldset
                legend={
                  <Text
                    fw={600}
                    c={MANTINE_THEME_A_COLORS.darkestGold}
                    size="sm"
                  >
                    Strategy Parameters
                  </Text>
                }
              >
                <Grid>
                  {getStrategyParameterFields(strategyForm.values.type)
                    .filter((field) => !field.key.startsWith("initial_"))
                    .map((field) => (
                      <Grid.Col key={field.key} span={6}>
                        {field.key === "name" ? (
                          <TextInput
                            label={field.label}
                            description={field.description}
                            placeholder={field.label}
                            value={
                              (strategyForm.values.parameters[
                                field.key
                              ] as string) || field.defaultValue
                            }
                            onChange={(event) =>
                              strategyForm.setFieldValue("parameters", {
                                ...strategyForm.values.parameters,
                                [field.key]: event.currentTarget.value,
                              })
                            }
                          />
                        ) : (
                          <NumberInput
                            label={field.label}
                            description={field.description}
                            placeholder={field.label}
                            step={
                              field.key.includes("_dev") ||
                              field.key.includes("threshold")
                                ? 0.01
                                : 1
                            }
                            value={
                              (strategyForm.values.parameters[
                                field.key
                              ] as number) || field.defaultValue
                            }
                            onChange={(value) =>
                              strategyForm.setFieldValue("parameters", {
                                ...strategyForm.values.parameters,
                                [field.key]:
                                  typeof value === "string"
                                    ? parseFloat(value) || field.defaultValue
                                    : value || field.defaultValue,
                              })
                            }
                          />
                        )}
                      </Grid.Col>
                    ))}
                </Grid>
              </Fieldset>
            )}

            <Group justify="flex-end" gap="sm">
              <Button variant="outline" onClick={closeStrategy}>
                Cancel
              </Button>
              <Button type="submit" disabled={!strategyForm.values.type}>
                Add Strategy
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={detailsOpened}
        onClose={closeDetails}
        title={`Asset Details - ${viewingAsset?.ticker || ""}`}
        size="lg"
      >
        {viewingAsset && (
          <Stack gap="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Configuration</Table.Th>
                  <Table.Th>Value</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Asset Ticker</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.ticker}</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Max Position Size (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.max_position_size_pct || 0}%</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Min Trade Size (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.min_trade_size_pct || 0}%</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Min Holding Candles</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.min_holding_candle || 0}</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Cool Down Period</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.cool_down_period || 0}</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Trailing Stop Loss (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.trailing_stop_loss_pct || 0}%</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Trailing Stop Update Threshold (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>
                      {viewingAsset.trailing_stop_update_threshold_pct || 0}%
                    </Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Take Profit (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.take_profit_pct || 0}%</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Risk Per Trade (%)</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.risk_per_trade_pct || 0}%</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Sell Fraction</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{viewingAsset.sell_fraction || 0}</Text>
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>
                    <Text fw={500}>Number of Strategies</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text>{(viewingAsset.strategies || []).length}</Text>
                  </Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>

            {(viewingAsset.strategies || []).length > 0 && (
              <>
                <Divider />
                <Text fw={600} size="sm">
                  Configured Strategies
                </Text>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Strategy Name</Table.Th>
                      <Table.Th>Parameters</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(viewingAsset.strategies || []).map((strategy, index) => {
                      const strategyType = Object.keys(strategy)[0];
                      const params = (strategy as any)[strategyType];
                      return (
                        <Table.Tr key={index}>
                          <Table.Td>
                            <Text fw={500}>{strategyType}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="xs" c="dimmed">
                              {Object.entries(params || {})
                                .map(([key, value]) => `${key}: ${value}`)
                                .join(", ")}
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </>
            )}

            <Group justify="flex-end">
              <Button onClick={closeDetails}>Close</Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </>
  );
}
