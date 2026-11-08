import React, { useEffect, useRef } from 'react';
import {
  createChart,
  CrosshairMode,
  CandlestickSeries,
  AreaSeries,
  LineSeries,
  HistogramSeries,
  createSeriesMarkers,
} from 'lightweight-charts';
import { TrendingUp } from 'lucide-react';
import { addTradingDays } from '../services/tradingDays';

function extractTradePlan(aiReport, history) {
  if (!history || history.length === 0) return null;
  const lastBar = history[history.length - 1];
  const close = parseFloat(lastBar.close || lastBar.Close);

  // Ưu tiên kế hoạch có cấu trúc (đã được backend kiểm tra nhất quán)
  const tp = aiReport?.trade_plan;
  if (tp && Number(tp.entry_low) > 0 && Number(tp.stop_loss) > 0) {
    return {
      buyMin: Number(tp.entry_low),
      buyMax: Number(tp.entry_high),
      stopLoss: Number(tp.stop_loss),
      target1: Number(tp.target_1) || null,
      target2: Number(tp.target_2) || null,
    };
  }

  let buyMin = null;
  let buyMax = null;
  let stopLoss = null;

  if (aiReport && aiReport.analysis) {
    // Regex matching: Vùng quan sát mua (Buy Zone) | 20.56 – 21.20 |
    const buyMatch = aiReport.analysis.match(/Vùng quan sát mua[^|]*\|\s*([\d.,]+)\s*[–-]\s*([\d.,]+)/i);
    if (buyMatch) {
      buyMin = parseFloat(buyMatch[1].replace(',', ''));
      buyMax = parseFloat(buyMatch[2].replace(',', ''));
    }
    // Regex matching: Cắt lỗ bắt buộc (Stop Loss) | 19.74 |
    const slMatch = aiReport.analysis.match(/Cắt lỗ bắt buộc[^|]*\|\s*([\d.,]+)/i);
    if (slMatch) {
      stopLoss = parseFloat(slMatch[1].replace(',', ''));
    }
  }

  // Fallback định lượng an toàn nếu không tìm thấy trong chuỗi Markdown
  if (!buyMin || isNaN(buyMin)) buyMin = Number((close * 0.98).toFixed(2));
  if (!buyMax || isNaN(buyMax)) buyMax = Number((close * 1.01).toFixed(2));
  if (!stopLoss || isNaN(stopLoss)) stopLoss = Number((close * 0.94).toFixed(2));

  return { buyMin, buyMax, stopLoss };
}

export default function StockChart({ history, predictions, aiReport }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!Array.isArray(history) || history.length === 0 || !chartContainerRef.current) return;

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 440,
      layout: { background: { type: 'solid', color: '#010409' }, textColor: '#8b949e', fontSize: 12 },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.08, bottom: 0.24 } },
      timeScale: { borderColor: '#30363d', timeVisible: true },
    });

    chartRef.current = chart;
    window.addEventListener('resize', handleResize);

    // 1. Candlestick Series (Nến giá)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3fb950',
      downColor: '#f85149',
      borderVisible: false,
      wickUpColor: '#3fb950',
      wickDownColor: '#f85149',
    });

    // 2. [P0-FE-03] Đường EMA10 & SMA20
    const ema10Series = chart.addSeries(LineSeries, {
      color: '#fbbf24',
      lineWidth: 1,
      title: 'EMA10',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const sma20Series = chart.addSeries(LineSeries, {
      color: '#a855f7',
      lineWidth: 1,
      title: 'SMA20',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 3. [P0-FE-03] Volume Histogram ở đáy biểu đồ
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.80, bottom: 0 },
    });

    const formattedHistory = history
      .map((item) => {
        const dateStr = item.Date ? item.Date.substring(0, 10) : null;
        if (!dateStr) return null;
        const closeVal = parseFloat(item.Close);
        if (isNaN(closeVal)) return null;
        const openVal = isNaN(parseFloat(item.Open)) ? closeVal : parseFloat(item.Open);
        const highVal = isNaN(parseFloat(item.High)) ? closeVal : parseFloat(item.High);
        const lowVal = isNaN(parseFloat(item.Low)) ? closeVal : parseFloat(item.Low);
        const volVal = isNaN(parseFloat(item.Volume)) ? 0 : parseFloat(item.Volume);
        const ema10Val = parseFloat(item.EMA10);
        const sma20Val = parseFloat(item.SMA20);

        return {
          time: dateStr,
          open: openVal,
          high: highVal,
          low: lowVal,
          close: closeVal,
          volume: volVal,
          ema10: !isNaN(ema10Val) && ema10Val > 0 ? ema10Val : null,
          sma20: !isNaN(sma20Val) && sma20Val > 0 ? sma20Val : null,
        };
      })
      .filter(Boolean);

    formattedHistory.sort((a, b) => a.time.localeCompare(b.time));

    const uniqueHistory = [];
    const ema10Data = [];
    const sma20Data = [];
    const volumeData = [];
    const seen = new Set();

    for (const h of formattedHistory) {
      if (!seen.has(h.time)) {
        seen.add(h.time);
        uniqueHistory.push({ time: h.time, open: h.open, high: h.high, low: h.low, close: h.close });
        if (h.ema10 !== null) ema10Data.push({ time: h.time, value: h.ema10 });
        if (h.sma20 !== null) sma20Data.push({ time: h.time, value: h.sma20 });
        volumeData.push({
          time: h.time,
          value: h.volume,
          color: h.close >= h.open ? 'rgba(63, 185, 80, 0.35)' : 'rgba(248, 81, 73, 0.35)',
        });
      }
    }

    candlestickSeries.setData(uniqueHistory);
    if (ema10Data.length > 0) ema10Series.setData(ema10Data);
    if (sma20Data.length > 0) sma20Series.setData(sma20Data);
    if (volumeData.length > 0) volumeSeries.setData(volumeData);

    // [P0-FE-01] Kích hoạt Buy/Sell Markers trên biểu đồ Candlestick
    const tradePlan = extractTradePlan(aiReport, uniqueHistory);
    if (tradePlan && uniqueHistory.length > 0) {
      const lastBar = uniqueHistory[uniqueHistory.length - 1];
      const markers = [
        {
          time: lastBar.time,
          position: 'belowBar',
          color: '#22c55e',
          shape: 'arrowUp',
          text: `MUA (${tradePlan.buyMin} - ${tradePlan.buyMax})`,
        },
        {
          time: lastBar.time,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: `CẮT LỖ (${tradePlan.stopLoss})`,
        },
      ];

      try {
        if (typeof candlestickSeries.setMarkers === 'function') {
          candlestickSeries.setMarkers(markers);
        } else if (typeof createSeriesMarkers === 'function') {
          createSeriesMarkers(candlestickSeries, markers);
        }
      } catch (err) {
        console.warn('Lỗi thiết lập markers trên biểu đồ:', err);
      }

      // Đường giá kế hoạch: vùng mua, cắt lỗ, mục tiêu
      const lines = [
        { price: tradePlan.buyMax, color: '#22c55e', title: 'Vùng mua ↑' },
        { price: tradePlan.buyMin, color: '#22c55e', title: 'Vùng mua ↓' },
        { price: tradePlan.stopLoss, color: '#ef4444', title: 'Cắt lỗ' },
        { price: tradePlan.target1, color: '#38bdf8', title: 'Mục tiêu 1' },
        { price: tradePlan.target2, color: '#38bdf8', title: 'Mục tiêu 2' },
      ];
      for (const l of lines) {
        if (!l.price || Number.isNaN(l.price)) continue;
        try {
          candlestickSeries.createPriceLine({
            price: l.price,
            color: l.color,
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: l.title,
          });
        } catch (err) {
          console.warn('Lỗi vẽ đường giá kế hoạch:', err);
        }
      }
    }

    // 4. [P0-FIN-01] Vùng dự báo tương lai (AreaSeries) tính bằng Trading Days
    if (Array.isArray(predictions) && predictions.length > 0 && uniqueHistory.length > 0) {
      const areaSeries = chart.addSeries(AreaSeries, {
        lineColor: '#2f81f7',
        topColor: 'rgba(47, 129, 247, 0.3)',
        bottomColor: 'rgba(47, 129, 247, 0.05)',
        lineWidth: 2,
        title: 'AI Dự báo',
      });

      const lastHist = uniqueHistory[uniqueHistory.length - 1];

      const chartPreds = predictions.map((pred) => {
        const days = pred.days_future || 1;
        const targetDay = addTradingDays(lastHist.time, days);
        return {
          time: targetDay.isoDate,
          value: (parseFloat(pred.high) + parseFloat(pred.low)) / 2,
        };
      });

      const uniquePreds = [];
      let lastD = lastHist.time;
      for (const p of chartPreds) {
        let d = p.time;
        if (d <= lastD) {
          const nextDay = addTradingDays(lastD, 1);
          d = nextDay.isoDate;
        }
        uniquePreds.push({ time: d, value: p.value });
        lastD = d;
      }
      uniquePreds.unshift({ time: lastHist.time, value: lastHist.close });
      areaSeries.setData(uniquePreds);
    }

    chart.timeScale().fitContent();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current === chart) {
        chart.remove();
        chartRef.current = null;
      }
    };
  }, [history, predictions, aiReport]);

  return (
    <div className="glass-panel chart-card">
      <div className="section-title" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={18} color="var(--accent-blue)" />
          <h2>Biểu Đồ Kỹ Thuật & Quỹ Đạo Dự Báo AI</h2>
        </div>
        <div className="chart-legend">
          <span className="legend-dot" style={{ color: '#fbbf24' }}>● EMA10</span>
          <span className="legend-dot" style={{ color: '#a855f7' }}>● SMA20</span>
          <span className="legend-dot" style={{ color: '#2f81f7' }}>● Dự báo AI</span>
        </div>
      </div>
      <div ref={chartContainerRef} className="chart-container" />
    </div>
  );
}
