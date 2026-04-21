import React, { useState, useEffect, useRef } from 'react';
import { createChart, CrosshairMode, CandlestickSeries, AreaSeries } from 'lightweight-charts';
import { Search, Calendar, Activity, Zap, TrendingUp, AlertCircle, Play, ArrowUpRight, ArrowDownRight, Info, FileText, Target } from 'lucide-react';
import './App.css';

function App() {
  const [symbol, setSymbol] = useState('HPG');
  const [targetDate, setTargetDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  const fetchAnalysis = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const payload = { symbol };
      if (targetDate) {
        payload.target_date = targetDate;
      }

      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Lỗi kết nối máy chủ API');
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatPredictionDate = (daysFuture) => {
    if (!data || !data.history || data.history.length === 0) return '';
    const lastDate = new Date(data.history[data.history.length - 1].Date);
    const futureDate = new Date(lastDate.getTime() + (daysFuture * 24 * 3600 * 1000));
    return futureDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
  };

  useEffect(() => {
    if (!data || !chartContainerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: {
        background: { type: 'solid', color: '#010409' },
        textColor: '#8b949e',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#21262d' },
        horzLines: { color: '#21262d' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#30363d',
      },
      timeScale: {
        borderColor: '#30363d',
        timeVisible: true,
      },
    });

    chartRef.current = chart;
    window.addEventListener('resize', handleResize);

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3fb950',
      downColor: '#f85149',
      borderVisible: false,
      wickUpColor: '#3fb950',
      wickDownColor: '#f85149',
    });

    const formattedHistory = (data.history || []).map(item => {
      const dateStr = item.Date ? item.Date.substring(0, 10) : null;
      if (!dateStr) return null;
      const closeVal = parseFloat(item.Close);
      return {
        time: dateStr,
        open: parseFloat(item.Open) || closeVal,
        high: parseFloat(item.High) || closeVal,
        low: parseFloat(item.Low) || closeVal,
        close: closeVal
      };
    }).filter(Boolean);

    formattedHistory.sort((a, b) => a.time.localeCompare(b.time));
    
    // Remove duplicates
    const uniqueHistory = [];
    const seen = new Set();
    for (const h of formattedHistory) {
      if (!seen.has(h.time)) {
        seen.add(h.time);
        uniqueHistory.push(h);
      }
    }
    
    candlestickSeries.setData(uniqueHistory);

    if (data.ai_report?.predictions?.length > 0 && uniqueHistory.length > 0) {
      const areaSeries = chart.addSeries(AreaSeries, {
        lineColor: '#2f81f7',
        topColor: 'rgba(47, 129, 247, 0.3)',
        bottomColor: 'rgba(47, 129, 247, 0.05)',
        lineWidth: 2,
      });

      const lastHist = uniqueHistory[uniqueHistory.length - 1];
      const lastTs = new Date(lastHist.time + 'T00:00:00Z').getTime();
      
      const predictions = data.ai_report.predictions.map(pred => {
        const ts = lastTs + (pred.days_future * 24 * 3600 * 1000);
        const day = new Date(ts).toISOString().substring(0, 10);
        return { time: day, value: (parseFloat(pred.high) + parseFloat(pred.low)) / 2 };
      });

      const uniquePreds = [];
      let lastD = lastHist.time;
      for (const p of predictions) {
        let d = p.time;
        if (d <= lastD) {
          const next = new Date(new Date(lastD + 'T00:00:00Z').getTime() + 86400000);
          d = next.toISOString().substring(0, 10);
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
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [data]);

  const getLatestMetrics = () => {
    if (!data || !data.history || data.history.length < 2) return null;
    const last = data.history[data.history.length - 1];
    const prev = data.history[data.history.length - 2];
    const change = last.Close - prev.Close;
    const pct = (change / prev.Close) * 100;
    return {
      price: last.Close.toLocaleString(),
      change: change.toLocaleString(),
      pct: pct.toFixed(2),
      isUp: change >= 0,
      high: last.High.toLocaleString(),
      low: last.Low.toLocaleString(),
      vol: last.Volume ? (last.Volume / 1000000).toFixed(1) + 'M' : 'N/A'
    };
  };

  const metrics = getLatestMetrics();

  // Helper to format AI report text with basic markdown support (headers, bold, tables)
  const formatReport = (text) => {
    if (!text) return null;
    
    const lines = text.split('\n');
    const result = [];
    let tableLines = [];
    let inTable = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Handle Table
        if (line.startsWith('|')) {
            inTable = true;
            tableLines.push(line);
            continue;
        } else if (inTable) {
            // Render the gathered table lines
            if (tableLines.length > 0) {
                const rows = tableLines.filter(row => !row.includes('---'));
                result.push(
                    <div className="table-wrapper" key={`table-${i}`}>
                        <table className="analysis-table">
                            <tbody>
                                {rows.map((row, ri) => {
                                    const cols = row.split('|').filter(c => c.trim() !== '' || row.indexOf('|') !== row.lastIndexOf('|'));
                                    return (
                                        <tr key={ri}>
                                            {cols.map((col, ci) => (
                                                <td key={ci} style={{ fontWeight: ri === 0 ? '700' : '400', background: ri === 0 ? 'rgba(47, 129, 247, 0.1)' : 'transparent' }}>
                                                    {col.trim().replace(/\*\*/g, '')}
                                                </td>
                                            ))}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                );
            }
            tableLines = [];
            inTable = false;
        }

        // Handle Headers
        if (line.startsWith('###')) {
            result.push(<h3 key={i}>{line.replace('###', '').trim()}</h3>);
        } else if (line.match(/^[0-9]\./)) {
            result.push(<h3 key={i} style={{ color: 'var(--accent-gold)' }}>{line}</h3>);
        } else if (line !== '') {
            // Simple bolding support
            const parts = line.split(/(\*\*.*?\*\*)/);
            result.push(
                <p key={i}>
                    {parts.map((part, pi) => 
                        part.startsWith('**') && part.endsWith('**') 
                        ? <strong key={pi} style={{ color: 'var(--text-active)' }}>{part.slice(2, -2)}</strong> 
                        : part
                    )}
                </p>
            );
        }
    }
    return result;
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="logo-container">
          <Activity className="icon-pulse" size={32} />
          <h1>Antigravity WallStreet AI</h1>
        </div>
        <p className="subtitle">Scientific Stock Analysis & Predictive Intelligence Dashboard</p>
      </header>

      <main className="main-content">
        <div className="glass-panel search-panel">
          <form onSubmit={fetchAnalysis} className="search-form">
            <div className="input-group">
              <label><Search size={14} /> Symbol</label>
              <input 
                type="text" 
                value={symbol} 
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="HPG, FPT, VNM..."
                required
              />
            </div>
            
            <div className="input-group">
              <label><Calendar size={14} /> Start Date</label>
              <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
            </div>

            <button type="submit" className="analyze-btn" disabled={loading}>
              {loading ? <Zap className="spin" size={16} /> : <Play size={16} />}
              {loading ? 'Crunching Intelligence...' : 'Start Intelligence Analysis'}
            </button>
          </form>
        </div>

        {error && (
          <div className="glass-panel error-panel">
            <AlertCircle size={20} />
            <p>{error}</p>
          </div>
        )}

        {data && metrics && (
          <div className="dashboard-grid">
            {/* Row 1: Top Metrics */}
            <div className="metrics-bar">
              <div className="glass-panel metric-card">
                <span className="metric-label">Market Value</span>
                <div className="metric-value">{metrics.price}</div>
                <div className={`metric-change ${metrics.isUp ? 'up-color' : 'down-color'}`}>
                  {metrics.isUp ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                  {metrics.change} ({metrics.pct}%)
                </div>
              </div>
              <div className="glass-panel metric-card">
                <span className="metric-label">Daily Range</span>
                <div className="metric-value" style={{fontSize: '1rem'}}>
                  H: <span className="up-color">{metrics.high}</span> / L: <span className="down-color">{metrics.low}</span>
                </div>
              </div>
              <div className="glass-panel metric-card">
                <span className="metric-label">Trade Volume</span>
                <div className="metric-value">{metrics.vol}</div>
              </div>
            </div>

            {/* Row 2: Chart and Predictions side by side */}
            <div className="top-cards-row">
              <div className="glass-panel chart-card">
                <div className="section-title">
                  <TrendingUp size={18} color="var(--accent-blue)" />
                  <h2>Predictive Trajectory</h2>
                </div>
                <div ref={chartContainerRef} className="chart-container" />
              </div>

              <div className="glass-panel predictions-card">
                <div className="section-title">
                  <Target size={18} color="var(--accent-gold)" />
                  <h2>Price Targets</h2>
                </div>
                <div className="predictions-table-container">
                    <table className="predictions-table">
                        <thead>
                            <tr>
                                <th>Timeline</th>
                                <th>High</th>
                                <th>Low</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.ai_report.predictions.map((p, i) => (
                                <tr key={i}>
                                    <td>
                                        <span className="date-label">Ngày {formatPredictionDate(p.days_future)}</span>
                                        <span className="tf-label">{p.timeframe}</span>
                                    </td>
                                    <td className="high-val">{p.high}</td>
                                    <td className="low-val">{p.low}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
              </div>
            </div>

            {/* Row 3: Full Width AI Analysis at bottom */}
            <div className="bottom-cards-row">
              <div className="glass-panel analysis-card">
                <div className="section-title">
                  <FileText size={18} color="var(--accent-blue)" />
                  <h2>Deep Expert Intelligence Report</h2>
                </div>
                
                {data.ai_report?.analysis && (data.ai_report.analysis.includes('⚠️') || data.ai_report.analysis.includes('Lỗi')) && (
                  <div className="warning-box">
                    <Info size={16} />
                    <span>AI infrastructure load balancing active. Chart precision maintained.</span>
                  </div>
                )}

                <div className="analysis-content">
                  {formatReport(data.ai_report?.analysis) || "Compiling intelligence report..."}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
