import { useEffect, useRef } from "react";

interface DataPoint {
  time: number;
  value: number;
}

interface LineSeries {
  name: string;
  data: DataPoint[];
  color: string;
}

interface LineChartProps {
  data: LineSeries[];
  height: number;
  width?: number;
}

export function LineChart({ data, height, width }: LineChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    // Get the container width
    const containerWidth = width || canvas.parentElement?.clientWidth || 800;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size to match container
    canvas.width = containerWidth;
    canvas.height = height;

    // Clear canvas
    ctx.clearRect(0, 0, containerWidth, height);

    // Find global min/max for scaling
    let globalMin = Infinity;
    let globalMax = -Infinity;
    let globalTimeMin = Infinity;
    let globalTimeMax = -Infinity;

    data.forEach((series) => {
      // If time is missing, use index as time
      series.data = series.data.map((point, idx) => ({
        ...point,
        time: point.time !== undefined ? point.time : idx,
      }));

      // Filter out invalid data points
      const validData = series.data.filter(
        (point) =>
          point.time !== undefined &&
          point.value !== undefined &&
          !isNaN(point.time) &&
          !isNaN(point.value) &&
          isFinite(point.time) &&
          isFinite(point.value)
      );

      if (validData.length !== series.data.length) {
        console.warn(
          `Series ${series.name}: Filtered out ${
            series.data.length - validData.length
          } invalid points`
        );
        series.data = validData;
      }

      series.data.forEach((point) => {
        globalMin = Math.min(globalMin, point.value);
        globalMax = Math.max(globalMax, point.value);
        globalTimeMin = Math.min(globalTimeMin, point.time);
        globalTimeMax = Math.max(globalTimeMax, point.time);
      });
    });

    // Check if we have valid data after filtering
    if (
      !isFinite(globalMin) ||
      !isFinite(globalMax) ||
      !isFinite(globalTimeMin) ||
      !isFinite(globalTimeMax)
    ) {
      console.error("No valid data points found after filtering");
      return;
    }

    // Add padding to min/max
    const valueRange = globalMax - globalMin;
    // Handle case where all values are the same
    const paddedMin =
      valueRange === 0 ? globalMin - 1 : globalMin - valueRange * 0.05;
    const paddedMax =
      valueRange === 0 ? globalMax + 1 : globalMax + valueRange * 0.05;

    const timeRange = globalTimeMax - globalTimeMin;
    // Handle case where all times are the same
    const paddedTimeMin =
      timeRange === 0 ? globalTimeMin - 1 : globalTimeMin - timeRange * 0.02;
    const paddedTimeMax =
      timeRange === 0 ? globalTimeMax + 1 : globalTimeMax + timeRange * 0.02;

    // Chart dimensions - restored left margin for y-axis values
    const margin = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartWidth = containerWidth - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Helper function to convert data coordinates to canvas coordinates
    const x = (time: number) => {
      const result =
        margin.left +
        ((time - paddedTimeMin) / (paddedTimeMax - paddedTimeMin)) * chartWidth;
      if (isNaN(result) || !isFinite(result)) {
        console.warn(`Invalid x coordinate: time=${time}, result=${result}`);
        return margin.left;
      }
      return result;
    };

    const y = (value: number) => {
      const result =
        margin.top +
        chartHeight -
        ((value - paddedMin) / (paddedMax - paddedMin)) * chartHeight;
      if (isNaN(result) || !isFinite(result)) {
        console.warn(`Invalid y coordinate: value=${value}, result=${result}`);
        return margin.top + chartHeight / 2;
      }
      return result;
    };

    // Draw grid lines
    ctx.strokeStyle = "#e0e0e0";
    ctx.lineWidth = 1;

    // Vertical grid lines (time)
    const timeSteps = 5;
    for (let i = 0; i <= timeSteps; i++) {
      const time =
        paddedTimeMin + (paddedTimeMax - paddedTimeMin) * (i / timeSteps);
      const xPos = x(time);
      ctx.beginPath();
      ctx.moveTo(xPos, margin.top);
      ctx.lineTo(xPos, margin.top + chartHeight);
      ctx.stroke();

      // Draw time labels horizontally
      const date = new Date(time * 1000);
      const timeLabel = date.toLocaleDateString();
      ctx.fillStyle = "#666";
      ctx.font = "12px Arial";
      ctx.textAlign = "center";
      ctx.fillText(timeLabel, xPos, margin.top + chartHeight + 20);
    }

    // Horizontal grid lines (value) - restored y-axis labels
    // Calculate a nice step for y-axis
    function niceStep(range: number) {
      if (range > 10000) return 1000;
      if (range > 1000) return 100;
      if (range > 100) return 10;
      if (range > 10) return 1;
      return 0.1;
    }
    const step = niceStep(paddedMax - paddedMin);
    const valueSteps = 5;
    for (let i = 0; i <= valueSteps; i++) {
      const value =
        Math.round(
          (paddedMin + (paddedMax - paddedMin) * (i / valueSteps)) / step
        ) * step;
      const yPos = y(value);
      ctx.beginPath();
      ctx.moveTo(margin.left, yPos);
      ctx.lineTo(margin.left + chartWidth, yPos);
      ctx.stroke();

      // Draw value labels
      const valueLabel = value.toLocaleString("en-US", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });
      ctx.fillStyle = "#666";
      ctx.font = "12px Arial";
      ctx.textAlign = "right";
      ctx.fillText(valueLabel, margin.left - 10, yPos + 4);
    }

    // Draw lines for each series
    data.forEach((series) => {
      if (series.data.length < 2) {
        console.log(
          `Series ${series.name} has insufficient data:`,
          series.data.length
        );
        return;
      }

      ctx.strokeStyle = series.color;
      ctx.lineWidth = 2;
      ctx.beginPath();

      // Move to first point
      const firstPoint = series.data[0];
      const firstX = x(firstPoint.time);
      const firstY = y(firstPoint.value);

      // Debug: Check if coordinates are valid
      if (isNaN(firstX) || isNaN(firstY)) {
        console.error(`Series ${series.name}: Invalid first point coordinates`);
        return;
      }

      ctx.moveTo(firstX, firstY);

      // Draw lines to subsequent points
      for (let i = 1; i < series.data.length; i++) {
        const point = series.data[i];
        const pointX = x(point.time);
        const pointY = y(point.value);
        ctx.lineTo(pointX, pointY);
      }

      ctx.stroke();
    });

    // Draw legend
    const legendY = margin.top - 10;
    data.forEach((series, index) => {
      const legendX = margin.left + index * 120;

      // Draw legend line
      ctx.strokeStyle = series.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(legendX, legendY);
      ctx.lineTo(legendX + 20, legendY);
      ctx.stroke();

      // Draw legend text
      ctx.fillStyle = "#333";
      ctx.font = "12px Arial";
      ctx.textAlign = "left";
      ctx.fillText(series.name, legendX + 25, legendY + 4);
    });
  }, [data, height, width]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: "100%",
        height: height,
        border: "1px solid #ddd",
        borderRadius: "4px",
        backgroundColor: "white",
      }}
    />
  );
}
