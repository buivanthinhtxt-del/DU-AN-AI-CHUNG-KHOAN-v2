import React, { useState, useEffect, useRef } from 'react';
import { createChart, CrosshairMode, CandlestickSeries, AreaSeries } from 'lightweight-charts';
import { Search, Calendar, Activity, Zap, TrendingUp, AlertCircle, Play, ArrowUpRight, ArrowDownRight, Info, FileText, Target, Bookmark, Trash2, Plus } from 'lucide-react';
import './App.css';
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', color: '#f85149' }}>
          <h2>CRASH DETECTED: {this.state.error?.toString()}</h2>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [symbol, setSymbol] = useState('HPG');
  const [targetDate, setTargetDate] = useState('');
  
  const [loadingMarket, setLoadingMarket] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  
  const [data, setData] = useState(null); // Market Data
  const [aiReport, setAiReport] = useState(null); // AI Data
  
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [typedAnalysis, setTypedAnalysis] = useState("");
  
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const typewriterRef = useRef(null);

  const fetchWatchlist = async () => {
     try {
       const res = await fetch('http://127.0.0.1:8000/api/watchlist');
       const j = await res.json();
       if (Array.isArray(j)) {
         setWatchlist(j);
       } else {
         setWatchlist([]);
       }
     } catch(e) {
       setWatchlist([]);
     }
  };
  
  useEffect(() => { fetchWatchlist(); }, []);

  const addToWatchlist = async (sym) => {
     await fetch('http://127.0.0.1:8000/api/watchlist', {
        method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol: sym})
     });
     fetchWatchlist();
  }
  
  const removeWatchlist = async (sym, e) => {
     e.stopPropagation();
     await fetch(`http://127.0.0.1:8000/api/watchlist/${sym}`, { method: 'DELETE' });
     fetchWatchlist();
  }

  const fetchAnalysis = async (e, forceSymbol) => {
    if (e) e.preventDefault();
    const targetSymbol = forceSymbol || symbol;
    setSymbol(targetSymbol);
    
    setLoadingMarket(true);
    setLoadingAI(false);
    setError(null);
    setData(null);
    setAiReport(null);
    setTypedAnalysis("");

    try {
      const payload = { symbol: targetSymbol };
      if (targetDate) payload.target_date = targetDate;

      // 1. Fetch Market Data Phase
      const mRes = await fetch('http://127.0.0.1:8000/api/market_data', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      
      if (!mRes.ok) {
        const errData = await mRes.json();
        throw new Error(errData.detail || 'Lỗi kết nối máy chủ API');
      }
      
      const marketData = await mRes.json();
      setData(marketData);
      setLoadingMarket(false);

      // 2. Fetch AI Report Phase
      setLoadingAI(true);
      const aiRes = await fetch('http://127.0.0.1:8000/api/ai_report', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      
      if (!aiRes.ok) {
        throw new Error("Lỗi phân tích AI. Đỉnh điểm giới hạn hoặc sập mạng.");
      }
      
      const aiData = await aiRes.json();
      setAiReport(aiData.ai_report);
      setLoadingAI(false);
      
      // Trigger Typewriter
      if (aiData.ai_report && aiData.ai_report.analysis) {
          if (typewriterRef.current) clearInterval(typewriterRef.current);
          let i = 0;
          setTypedAnalysis("");
          const text = aiData.ai_report.analysis;
          // Very fast typewriter
          typewriterRef.current = setInterval(() => {
              setTypedAnalysis((prev) => prev + text.charAt(i));
              i++;
              if (i >= text.length) clearInterval(typewriterRef.current);
          }, 8);
      }

    } catch (err) {
      if (err.message === "Failed to fetch") {
        setError("Lỗi Mạng (Failed to fetch): Máy chủ Backend (Python/FastAPI) không phản hồi hoặc cổng 8000 bị tắt. Hãy kiểm tra lại cửa sổ Terminal chạy API!");
      } else {
        setError(err.message);
      }
      setLoadingMarket(false);
      setLoadingAI(false);
    }
  };

  const formatPredictionDate = (daysFuture) => {
    if (!data || !data.history || data.history.length === 0) return '';
    const lastDate = new Date(data.history[data.history.length - 1].Date);
    const futureDate = new Date(lastDate.getTime() + (daysFuture * 24 * 3600 * 1000));
    return futureDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
  };

  const getSanitizedPredictions = () => {
      if (!aiReport || !Array.isArray(aiReport.predictions)) return [];
      if (!data || !Array.isArray(data.history) || data.history.length === 0) return aiReport.predictions;
      
      const lastHist = data.history[data.history.length - 1];
      const lastClose = lastHist.Close;
      
      return aiReport.predictions.map(p => {
          let rawH = p.high !== undefined ? p.high : (p.High || p.HIGH || '');
          let rawL = p.low !== undefined ? p.low : (p.Low || p.LOW || '');
          
          let hStr = rawH !== null && rawH !== undefined ? rawH.toString() : '';
          let lStr = rawL !== null && rawL !== undefined ? rawL.toString() : '';
          
          let h = parseFloat(hStr.replace(/,/g, ''));
          let l = parseFloat(lStr.replace(/,/g, ''));
          
          if (isNaN(h) || h === 0) h = lastClose * 1.05;
          if (isNaN(l) || l === 0) l = lastClose * 0.95;
          let d = parseInt(p.days_future);
          if (isNaN(d)) d = 7;
          
          return {
             ...p,
             high: h.toFixed(2),
             low: l.toFixed(2),
             days_future: d
          };
      });
  };

  useEffect(() => {
    if (!data || !chartContainerRef.current) return;

    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 420,
      layout: { background: { type: 'solid', color: '#010409' }, textColor: '#8b949e', fontSize: 12 },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#30363d' },
      timeScale: { borderColor: '#30363d', timeVisible: true },
    });

    chartRef.current = chart;
    window.addEventListener('resize', handleResize);

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#3fb950', downColor: '#f85149', borderVisible: false, wickUpColor: '#3fb950', wickDownColor: '#f85149',
    });

    const formattedHistory = Array.isArray(data?.history) ? data.history.map(item => {
      const dateStr = item.Date ? item.Date.substring(0, 10) : null;
      if (!dateStr) return null;
      let closeVal = parseFloat(item.Close);
      if (isNaN(closeVal)) return null;
      let openVal = parseFloat(item.Open);
      let highVal = parseFloat(item.High);
      let lowVal = parseFloat(item.Low);
      if (isNaN(openVal)) openVal = closeVal;
      if (isNaN(highVal)) highVal = closeVal;
      if (isNaN(lowVal)) lowVal = closeVal;
      return { time: dateStr, open: openVal, high: highVal, low: lowVal, close: closeVal };
    }).filter(Boolean) : [];

    formattedHistory.sort((a, b) => a.time.localeCompare(b.time));
    
    const uniqueHistory = [];
    const seen = new Set();
    for (const h of formattedHistory) {
      if (!seen.has(h.time)) { seen.add(h.time); uniqueHistory.push(h); }
    }
    
    candlestickSeries.setData(uniqueHistory);

    const preds = getSanitizedPredictions();
    if (preds.length > 0 && uniqueHistory.length > 0) {
      const areaSeries = chart.addSeries(AreaSeries, { lineColor: '#2f81f7', topColor: 'rgba(47, 129, 247, 0.3)', bottomColor: 'rgba(47, 129, 247, 0.05)', lineWidth: 2 });
      const lastHist = uniqueHistory[uniqueHistory.length - 1];
      const lastTs = new Date(lastHist.time + 'T00:00:00Z').getTime();
      
      const chartPreds = preds.map(pred => {
        let ts = lastTs + (pred.days_future * 24 * 3600 * 1000);
        let dayStr;
        try { dayStr = new Date(ts).toISOString().substring(0, 10); } 
        catch(e) { dayStr = new Date(lastTs + 7 * 86400000).toISOString().substring(0, 10); }
        return { time: dayStr, value: (parseFloat(pred.high) + parseFloat(pred.low)) / 2 };
      });

      const uniquePreds = [];
      let lastD = lastHist.time;
      for (const p of chartPreds) {
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
      if (chartRef.current === chart) {
        chart.remove();
        chartRef.current = null;
      }
    };
  }, [data, aiReport]);

  const getLatestMetrics = () => {
    if (!data || !data.history || data.history.length < 2) return null;
    const last = data.history[data.history.length - 1];
    const prev = data.history[data.history.length - 2];
    const change = last.Close - prev.Close;
    const pct = (change / prev.Close) * 100;
    return {
      price: last.Close.toLocaleString(), change: change.toLocaleString(), pct: pct.toFixed(2),
      isUp: change >= 0, high: last.High.toLocaleString(), low: last.Low.toLocaleString(),
      vol: last.Volume ? (last.Volume / 1000000).toFixed(1) + 'M' : 'N/A'
    };
  };

  const renderRadarChart = (scoresObj) => {
    if (!scoresObj) return null;
    const labels = ["Vĩ mô & Ngành", "FA & Catalyst", "TA & Xu hướng", "Dòng tiền", "Chiến lược"];
    const keys = ["macro_industry", "fundamentals_catalyst", "technical_momentum", "comparative_strength", "action_strategy"];
    const size = 260; const center = size / 2; const radius = (size / 2) - 35; 
    
    const getPoint = (val, index, total) => {
      const angle = (Math.PI * 2 * index) / total - Math.PI / 2;
      const r = (val / 100) * radius;
      return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
    };

    const total = 5; const ticks = [20, 40, 60, 80, 100];
    const webs = ticks.map(t => {
      const pts = Array.from({length: total}).map((_, i) => Object.values(getPoint(t, i, total)).join(',')).join(' ');
      return <polygon key={`web-${t}`} points={pts} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />;
    });

    const scorePts = keys.map((k, i) => {
       const v = scoresObj[k]?.score || 0;
       return Object.values(getPoint(v, i, total)).join(',');
    }).join(' ');

    const labelEls = keys.map((k, i) => {
       const pt = getPoint(125, i, total);
       return <text key={`lbl-${i}`} x={pt.x} y={pt.y} fill="var(--text-secondary)" fontSize="11" textAnchor="middle" dominantBaseline="middle">{labels[i]}</text>;
    });

    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {webs}
        <polygon points={scorePts} fill="rgba(47, 129, 247, 0.25)" stroke="var(--accent-blue)" strokeWidth="2" />
        {keys.map((k, i) => {
          const v = scoresObj[k]?.score || 0;
          const pt = getPoint(v, i, total);
          return <circle key={`dot-${i}`} cx={pt.x} cy={pt.y} r="4" fill="var(--accent-gold)" />;
        })}
        {labelEls}
      </svg>
    );
  };

  const renderProgressBars = (scoresObj) => {
     if (!scoresObj) return null;
     const items = [
       { key: "macro_industry", label: "🌍 BƯỚC 1: Vĩ mô & Sóng ngành" },
       { key: "fundamentals_catalyst", label: "🏢 BƯỚC 2: Cơ bản & Chất xúc tác" },
       { key: "technical_momentum", label: "📈 BƯỚC 3: Kỹ thuật & Xu hướng" },
       { key: "comparative_strength", label: "🧱 BƯỚC 4: Dòng tiền & Sức mạnh (So sánh)" },
       { key: "action_strategy", label: "🎯 BƯỚC 5: Chiến lược & Kịch bản hành động" }
     ];

     return items.map((item, idx) => {
        const val = scoresObj[item.key]?.score || 0;
        const reason = scoresObj[item.key]?.reason || "Chưa có dữ liệu đánh giá";
        let color = '#f85149'; if (val >= 40) color = '#d29922'; if (val >= 70) color = '#3fb950'; 

        return (
          <div key={idx} className="progress-item" style={{ marginBottom: '14px' }}>
             <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-active)', fontWeight: '600' }}>{item.label}</span>
                <span style={{ color: color, fontWeight: 'bold' }}>{val}/100</span>
             </div>
             <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${val}%`, height: '100%', background: color, transition: 'width 1s ease-out' }}></div>
             </div>
             <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px', fontStyle: 'italic', lineHeight: '1.4' }}>
               ↳ {reason}
             </div>
          </div>
        );
     });
  };

  const formatReport = (text) => {
    if (!text || typeof text !== 'string') return null;
    const lines = text.split('\n');
    const result = [];
    let tableLines = []; let inTable = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('|')) {
            inTable = true; tableLines.push(line); continue;
        } else if (inTable) {
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
            tableLines = []; inTable = false;
        }

        if (line.startsWith('###')) { result.push(<h3 key={i}>{line.replace('###', '').trim()}</h3>); } 
        else if (line.match(/^[0-9]\./)) { result.push(<h3 key={i} style={{ color: 'var(--accent-gold)' }}>{line}</h3>); } 
        else if (line !== '') {
            const parts = line.split(/(\*\*.*?\*\*)/);
            const isListItem = line.startsWith('-') || line.startsWith('+');
            result.push(
                <p key={i} style={{ 
                    textAlign: 'left', 
                    marginLeft: isListItem ? '1.5rem' : '0',
                    textIndent: isListItem ? '-1rem' : '0' 
                }}>
                    {parts.map((part, pi) => part.startsWith('**') && part.endsWith('**') ? <strong key={pi} style={{ color: 'var(--text-active)' }}>{part.slice(2, -2)}</strong> : part)}
                </p>
            );
        }
    }
    return result;
  };

  const metrics = getLatestMetrics();
  const sanitizedPreds = getSanitizedPredictions();

  return (
    <div className="App">
      
      {/* Sidebar Layout */}
      <aside className="sidebar glass-panel">
        <div className="sidebar-header">
           <Bookmark size={18} /> 
           <span>My Blueprint</span>
        </div>
        <div className="watchlist-items">
           {Array.isArray(watchlist) && watchlist.map((item, idx) => (
             <div className="watchlist-item" key={idx} onClick={() => fetchAnalysis(null, item.symbol)}>
                <span className="watchlist-item-symbol">{item.symbol}</span>
                <button className="watchlist-item-delete" onClick={(e) => removeWatchlist(item.symbol, e)}><Trash2 size={14}/></button>
             </div>
           ))}
           {(!Array.isArray(watchlist) || watchlist.length === 0) && <div style={{color: 'var(--text-secondary)', fontSize: '0.85rem', fontStyle: 'italic'}}>Follow list trống.</div>}
        </div>
      </aside>

      <main className="main-wrapper">
        <header className="app-header">
          <div className="logo-container" style={{justifyContent: 'center'}}>
            <Activity className="icon-pulse" size={32} />
            <h1>Antigravity WallStreet AI</h1>
          </div>
          <p className="subtitle">Scientific Stock Analysis & Predictive Intelligence Dashboard</p>
        </header>

        <div className="glass-panel search-panel">
          <form onSubmit={fetchAnalysis} className="search-form">
            <div className="input-group">
              <label><Search size={14} /> Symbol</label>
              <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="HPG, FPT, VNM..." required />
            </div>
            
            <div className="input-group">
              <label><Calendar size={14} /> Start Date</label>
              <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
            </div>

            <button type="submit" className="analyze-btn" disabled={loadingMarket}>
              {loadingMarket ? <Zap className="spin" size={16} /> : <Play size={16} />}
              {loadingMarket ? 'Loading Pipeline...' : 'Start Intelligence Analysis'}
            </button>
          </form>
        </div>

        {error && (
          <div className="glass-panel error-panel" style={{marginBottom: '1rem'}}>
            <AlertCircle size={20} />
            <p>{error}</p>
          </div>
        )}

        {loadingMarket && !data && (
          <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
            <Zap className="spin icon-pulse" size={48} color="var(--accent-blue)" style={{ margin: '0 auto 1.5rem', display: 'block' }} />
            <h3 style={{ color: 'var(--text-active)' }}>Đang lấy dữ liệu thị trường và lịch sử biểu đồ...</h3>
          </div>
        )}

        {data && (
          <div className="dashboard-grid">
            {data.macro && (
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                 <div className="macro-ticker" style={{marginBottom: 0, flex: 1}}>
                    <div className="macro-item"><span className="macro-label">Gold (GC=F):</span><span className={data.macro.GOLD?.includes('+') ? 'up-color' : (data.macro.GOLD?.includes('-') ? 'down-color' : '')}>{data.macro.GOLD}</span></div>
                    <div className="macro-item"><span className="macro-label">Brent Oil (BZ=F):</span><span className={data.macro.OIL?.includes('+') ? 'up-color' : (data.macro.OIL?.includes('-') ? 'down-color' : '')}>{data.macro.OIL}</span></div>
                    <div className="macro-item"><span className="macro-label">USD/VND:</span><span className={data.macro.USD_VND?.includes('+') ? 'up-color' : (data.macro.USD_VND?.includes('-') ? 'down-color' : '')}>{data.macro.USD_VND}</span></div>
                 </div>
                 <button className="add-watchlist-btn" onClick={() => addToWatchlist(data.symbol)} style={{marginLeft: '1rem'}}>
                    <Plus size={14}/> Bỏ túi mã này
                 </button>
              </div>
            )}

            {metrics && (
              <div className="metrics-bar">
                <div className="glass-panel metric-card"><span className="metric-label">Market Value</span><div className="metric-value">{metrics.price}</div><div className={`metric-change ${metrics.isUp ? 'up-color' : 'down-color'}`}>{metrics.isUp ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />} {metrics.change} ({metrics.pct}%)</div></div>
                <div className="glass-panel metric-card"><span className="metric-label">Daily Range</span><div className="metric-value" style={{fontSize: '1rem'}}>H: <span className="up-color">{metrics.high}</span> / L: <span className="down-color">{metrics.low}</span></div></div>
                <div className="glass-panel metric-card"><span className="metric-label">Trade Volume</span><div className="metric-value">{metrics.vol}</div></div>
              </div>
            )}

            <div className="top-cards-row">
              <div className="glass-panel chart-card">
                <div className="section-title"><TrendingUp size={18} color="var(--accent-blue)" /><h2>Predictive Trajectory</h2></div>
                <div ref={chartContainerRef} className="chart-container" />
              </div>

              <div className="glass-panel predictions-card">
                <div className="section-title"><Target size={18} color="var(--accent-gold)" /><h2>Price Targets</h2></div>
                <div className="predictions-table-container">
                    <table className="predictions-table">
                        <thead><tr><th>Timeline</th><th>High</th><th>Low</th><th>Động lực / Ghi chú</th></tr></thead>
                        <tbody>
                            {sanitizedPreds.map((p, i) => (
                                <tr key={i}>
                                    <td><span className="date-label">Ngày {formatPredictionDate(p.days_future)}</span><span className="tf-label">{p.timeframe || 'Tương lai'}</span></td>
                                    <td className="high-val">{p.high}</td>
                                    <td className="low-val">{p.low}</td>
                                    <td style={{fontSize: '0.75rem', color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: '1.4', maxWidth: '180px'}}>{p.reason || '-'}</td>
                                </tr>
                            ))}
                            {sanitizedPreds.length === 0 && !loadingAI && <tr><td colSpan="4" style={{textAlign: 'center'}}>Chưa có dự báo</td></tr>}
                            {loadingAI && <tr><td colSpan="4" style={{textAlign: 'center'}}><span className="typewriter-cursor" style={{margin: '0 auto'}}></span></td></tr>}
                        </tbody>
                    </table>
                </div>
              </div>
            </div>

            {loadingAI && !aiReport && (
              <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', border: '1px solid var(--accent-gold)' }}>
                 <p style={{color: 'var(--accent-gold)', fontWeight: 'bold'}}>&gt; Siêu máy tính AI đang tính toán đa chiều và gõ báo cáo...</p>
                 <span className="typewriter-cursor"></span>
              </div>
            )}

            {aiReport?.scores && (
              <div className="bottom-cards-row">
                <div className="glass-panel analysis-card">
                  <div className="section-title">
                    <Activity size={18} color="var(--accent-gold)" />
                    <h2>Bảng Chấm Điểm 5 Chiều Thực Chiến</h2>
                    <span style={{ marginLeft: 'auto', background: (aiReport.overall_score || 0) > 65 ? '#3fb950' : (aiReport.overall_score || 0) < 40 ? '#f85149' : 'var(--accent-gold)', color: '#010409', padding: '4px 12px', borderRadius: '6px', fontWeight: 'bold' }}>
                      Điểm tổng hợp: {aiReport.overall_score || 'N/A'}/100
                    </span>
                  </div>
                  <div className="scoring-container" style={{ display: 'flex', gap: '3rem', marginTop: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                    <div className="radar-chart" style={{ flex: '1', minWidth: '250px', display: 'flex', justifyContent: 'center' }}>{renderRadarChart(aiReport.scores)}</div>
                    <div className="progress-bars" style={{ flex: '2', minWidth: '300px', display: 'flex', flexDirection: 'column' }}>{renderProgressBars(aiReport.scores)}</div>
                  </div>
                </div>
              </div>
            )}

            {(aiReport?.analysis || typedAnalysis) && (
              <div className="bottom-cards-row">
                <div className="glass-panel analysis-card">
                  <div className="section-title">
                    <FileText size={18} color="var(--accent-blue)" />
                    <h2>Deep Expert Intelligence Report</h2>
                  </div>
                  
                  {(aiReport?.analysis?.includes('Lỗi') || aiReport?.analysis?.includes('Nội dung phân tích')) && (
                     <div className="warning-box"><Info size={16} /><span>AI infrastructure recovering from quota exceeded limit.</span></div>
                  )}

                  <div className="analysis-content">
                    {formatReport(typedAnalysis || aiReport?.analysis)}
                    {typedAnalysis.length > 0 && typedAnalysis.length < (aiReport?.analysis?.length || 0) && <span className="typewriter-cursor"></span>}
                  </div>
                </div>
              </div>
            )}

          </div>
        )}
      </main>
    </div>
  );
}

export default function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
