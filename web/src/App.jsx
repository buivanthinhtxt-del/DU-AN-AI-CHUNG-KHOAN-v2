import React, { useState, useEffect } from 'react';
import { Search, Calendar, Activity, Zap, Play, ArrowUpRight, ArrowDownRight, AlertCircle } from 'lucide-react';
import './App.css';

import StockChart from './components/StockChart';
import RadarScoreCard from './components/RadarScoreCard';
import PriceTargetsAndPeers from './components/PriceTargetsAndPeers';
import AnalysisReport from './components/AnalysisReport';
import MacroTicker from './components/MacroTicker';
import Sidebar from './components/Sidebar';
import AIChatBox from './components/AIChatBox';
import InvestmentThesis from './components/InvestmentThesis';

const HORIZON_OPTIONS = ['Lướt sóng (1–4 tuần)', 'Swing (1–3 tháng)', 'Trung hạn (3–12 tháng)', 'Dài hạn (> 1 năm)'];
const RISK_OPTIONS = ['Thấp', 'Trung bình', 'Cao'];

import {
  fetchMarketDataApi,
  fetchAiReportApi,
  getWatchlist,
  addToWatchlistApi,
  removeFromWatchlistApi,
} from './services/apiClient';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', color: '#f85149' }}>
          <h2>SỰ CỐ KHỞI TẠO GIAO DIỆN: {this.state.error?.toString()}</h2>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [symbol, setSymbol] = useState('HPG');
  const [targetDate, setTargetDate] = useState('');
  const [horizon, setHorizon] = useState('Swing (1–3 tháng)');
  const [riskProfile, setRiskProfile] = useState('Trung bình');
  const [costBasis, setCostBasis] = useState('');

  const [loadingMarket, setLoadingMarket] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);

  const [data, setData] = useState(null); // Market Data
  const [aiReport, setAiReport] = useState(null); // AI Data
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);

  const refreshWatchlist = async () => {
    const list = await getWatchlist();
    setWatchlist(list);
  };

  useEffect(() => {
    let isMounted = true;
    getWatchlist().then((list) => {
      if (isMounted) setWatchlist(list);
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleAddToWatchlist = async (sym) => {
    await addToWatchlistApi(sym);
    refreshWatchlist();
  };

  const handleRemoveWatchlist = async (sym, e) => {
    e.stopPropagation();
    await removeFromWatchlistApi(sym);
    refreshWatchlist();
  };

  const fetchAnalysis = async (e, forceSymbol) => {
    if (e) e.preventDefault();
    const targetSymbol = (forceSymbol || symbol).toUpperCase().trim();
    setSymbol(targetSymbol);

    setLoadingMarket(true);
    setLoadingAI(false);
    setError(null);
    setData(null);
    setAiReport(null);

    try {
      const payload = { symbol: targetSymbol };
      if (targetDate) payload.target_date = targetDate;

      // 1. Tải dữ liệu thị trường và lịch sử nến
      const marketData = await fetchMarketDataApi(payload);
      setData(marketData);
      setLoadingMarket(false);

      // 2. Tải báo cáo AI chuyên sâu (kèm hồ sơ nhà đầu tư để lời khuyên đúng hoàn cảnh)
      setLoadingAI(true);
      const aiPayload = { ...payload, horizon, risk_profile: riskProfile };
      const cost = parseFloat(String(costBasis).replace(',', '.'));
      if (!Number.isNaN(cost) && cost > 0) aiPayload.cost_basis = cost;
      const aiData = await fetchAiReportApi(aiPayload);
      setAiReport(aiData.ai_report);
      setLoadingAI(false);
    } catch (err) {
      setError(err.message || 'Đã xảy ra lỗi khi kết nối máy chủ.');
      setLoadingMarket(false);
      setLoadingAI(false);
    }
  };

  const getLatestMetrics = () => {
    if (!data || !data.history || data.history.length < 2) return null;
    const last = data.history[data.history.length - 1];
    const prev = data.history[data.history.length - 2];
    const change = last.Close - prev.Close;
    const pct = prev.Close !== 0 ? (change / prev.Close) * 100 : 0;
    return {
      price: Number(last.Close).toLocaleString(),
      change: (change >= 0 ? '+' : '') + Number(change).toFixed(2),
      pct: (pct >= 0 ? '+' : '') + pct.toFixed(2),
      isUp: change >= 0,
      high: Number(last.High).toLocaleString(),
      low: Number(last.Low).toLocaleString(),
      vol: last.Volume ? (last.Volume / 1000000).toFixed(1) + 'M' : 'N/A',
    };
  };

  const metrics = getLatestMetrics();
  const lastHistoryDate = data?.history && data.history.length > 0
    ? data.history[data.history.length - 1].Date
    : null;

  return (
    <div className="App">
      <Sidebar
        watchlist={watchlist}
        currentSymbol={symbol}
        onSelectSymbol={(sym) => fetchAnalysis(null, sym)}
        onRemoveSymbol={handleRemoveWatchlist}
      />

      <main className="main-wrapper">
        <header className="app-header">
          <div className="logo-container" style={{ justifyContent: 'center' }}>
            <Activity className="icon-pulse" size={32} />
            <h1>Antigravity WallStreet AI</h1>
          </div>
          <p className="subtitle">Scientific Stock Analysis & Predictive Intelligence Dashboard</p>
        </header>

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
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </div>

            <div className="input-group">
              <label>Khung đầu tư</label>
              <select className="profile-select" value={horizon} onChange={(e) => setHorizon(e.target.value)}>
                {HORIZON_OPTIONS.map((h) => (
                  <option key={h} value={h}>{h}</option>
                ))}
              </select>
            </div>

            <div className="input-group">
              <label>Khẩu vị rủi ro</label>
              <select className="profile-select" value={riskProfile} onChange={(e) => setRiskProfile(e.target.value)}>
                {RISK_OPTIONS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div className="input-group">
              <label>Giá vốn (nếu đang giữ)</label>
              <input
                type="text"
                inputMode="decimal"
                value={costBasis}
                onChange={(e) => setCostBasis(e.target.value)}
                placeholder="VD: 23.5 (nghìn đồng)"
                style={{ width: '150px' }}
              />
            </div>

            <button type="submit" className="analyze-btn" disabled={loadingMarket || loadingAI}>
              {loadingMarket ? <Zap className="spin" size={16} /> : <Play size={16} />}
              {loadingMarket ? 'Loading Pipeline...' : 'Start Intelligence Analysis'}
            </button>
          </form>
        </div>

        {error && (
          <div className="glass-panel error-panel" style={{ marginBottom: '1rem' }}>
            <AlertCircle size={20} />
            <p>{error}</p>
          </div>
        )}

        {loadingMarket && !data && (
          <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
            <Zap
              className="spin icon-pulse"
              size={48}
              color="var(--accent-blue)"
              style={{ margin: '0 auto 1.5rem', display: 'block' }}
            />
            <h3 style={{ color: 'var(--text-active)' }}>
              Đang tổng hợp dữ liệu giao dịch và lịch sử biểu đồ đa nguồn...
            </h3>
          </div>
        )}

        {data?.data_source?.warning && (
          <div className="glass-panel warning-box" style={{ marginBottom: '1rem' }}>
            <AlertCircle size={16} />
            <span>
              {data.data_source.warning} (dữ liệu đến {data.data_source.last_date}). Kiểm tra nguồn dữ liệu tại{' '}
              <code>/api/data_sources/health</code> hoặc cấu hình SSI FastConnect trong <code>.env</code>.
            </span>
          </div>
        )}

        {data && (
          <div className="dashboard-grid">
            {data.macro && (
              <MacroTicker
                macro={data.macro}
                symbol={data.symbol}
                sector={data.sector}
                onAddWatchlist={handleAddToWatchlist}
              />
            )}

            {metrics && (
              <div className="metrics-bar">
                <div className="glass-panel metric-card">
                  <span className="metric-label">Market Value</span>
                  <div className="metric-value">{metrics.price}</div>
                  <div className={`metric-change ${metrics.isUp ? 'up-color' : 'down-color'}`}>
                    {metrics.isUp ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                    {' '}{metrics.change} ({metrics.pct}%)
                  </div>
                </div>
                <div className="glass-panel metric-card">
                  <span className="metric-label">Daily Range</span>
                  <div className="metric-value" style={{ fontSize: '1rem' }}>
                    H: <span className="up-color">{metrics.high}</span> / L: <span className="down-color">{metrics.low}</span>
                  </div>
                </div>
                <div className="glass-panel metric-card">
                  <span className="metric-label">Trade Volume</span>
                  <div className="metric-value">{metrics.vol}</div>
                </div>
              </div>
            )}

            <div className="top-cards-row">
              <StockChart
                history={data.history}
                predictions={aiReport?.predictions}
                aiReport={aiReport}
              />

              <PriceTargetsAndPeers
                predictions={aiReport?.predictions || []}
                lastHistoryDate={lastHistoryDate}
                loadingAI={loadingAI}
                peers={data.peers}
                symbol={data.symbol}
                sector={data.sector}
                onSelectSymbol={(sym) => fetchAnalysis(null, sym)}
              />
            </div>

            {loadingAI && !aiReport && (
              <div
                className="glass-panel"
                style={{ padding: '2rem', textAlign: 'center', border: '1px solid var(--accent-gold)' }}
              >
                <p style={{ color: 'var(--accent-gold)', fontWeight: 'bold' }}>
                  &gt; Hội đồng đầu tư AI đang tra cứu BCTC, khối ngoại, vùng giá và lập kế hoạch (có thể mất 1–3 phút)...
                </p>
                <span className="typewriter-cursor"></span>
              </div>
            )}

            {aiReport?.trade_plan && <InvestmentThesis report={aiReport} />}

            {aiReport?.scores && (
              <RadarScoreCard
                scores={aiReport.scores}
                overallScore={aiReport.overall_score}
                summary={aiReport.summary}
              />
            )}

            {aiReport?.analysis && (
              <AnalysisReport
                analysisText={aiReport.analysis}
                news={data.news}
                engine={aiReport.engine}
              />
            )}
          </div>
        )}

        {/* AI Gemini Real-time Chatbox & Web Grounding */}
        <AIChatBox
          currentSymbol={data?.symbol || symbol}
          currentSector={data?.sector}
        />
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
