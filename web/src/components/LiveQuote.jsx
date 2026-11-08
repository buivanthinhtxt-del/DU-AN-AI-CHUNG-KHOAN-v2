import React, { useEffect, useRef, useState } from 'react';
import { createChart, AreaSeries, HistogramSeries, LineStyle } from 'lightweight-charts';
import { Radio } from 'lucide-react';
import { fetchRealtimeQuoteApi, fetchIntradayApi } from '../services/apiClient';

const QUOTE_POLL_MS = 10_000;
const INTRADAY_POLL_MS = 60_000;

// Màu chuẩn bảng giá Việt Nam: trần tím, sàn xanh lơ, tham chiếu vàng, tăng xanh, giảm đỏ
const COLORS = { ceiling: '#c084fc', floor: '#22d3ee', ref: '#fbbf24', up: '#10b981', down: '#ef4444' };

const SESSION_LABELS = {
  ATO: 'Phiên mở cửa (ATO)',
  LO: 'Khớp lệnh liên tục',
  CONTINUOUS: 'Khớp lệnh liên tục',
  INTERMISSION: 'Nghỉ trưa',
  BREAK: 'Nghỉ trưa',
  ATC: 'Phiên đóng cửa (ATC)',
  PT: 'Giao dịch thỏa thuận',
  PLO: 'Khớp lệnh sau giờ (PLO)',
  ENDED: 'Đã đóng cửa',
  CLOSED: 'Đã đóng cửa',
};

function priceColor(p, q) {
  if (!p || !q) return 'var(--text-active)';
  if (q.ceiling && p >= q.ceiling) return COLORS.ceiling;
  if (q.floor && p <= q.floor) return COLORS.floor;
  if (!q.ref || Math.abs(p - q.ref) < 1e-9) return COLORS.ref;
  return p > q.ref ? COLORS.up : COLORS.down;
}

const fmtPrice = (v) =>
  v == null ? '—' : Number(v).toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtInt = (v) => (v == null ? '—' : Math.round(Number(v)).toLocaleString('vi-VN'));
const fmtBn = (v, sign = false) =>
  v == null ? '—' : `${sign && v > 0 ? '+' : ''}${Number(v).toLocaleString('vi-VN', { maximumFractionDigits: 2 })} tỷ`;
const fmtTime = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleTimeString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
};

function IntradayChart({ bars, refPrice }) {
  const boxRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const refLineRef = useRef(null);

  useEffect(() => {
    if (!boxRef.current) return undefined;
    const chart = createChart(boxRef.current, {
      width: boxRef.current.clientWidth,
      height: 190,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#8b949e', fontSize: 11 },
      grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
      rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.1, bottom: 0.28 } },
      timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: false },
      handleScroll: false,
      handleScale: false,
    });
    const price = chart.addSeries(AreaSeries, {
      lineColor: '#3b82f6',
      topColor: 'rgba(59,130,246,0.28)',
      bottomColor: 'rgba(59,130,246,0.02)',
      lineWidth: 2,
      priceLineVisible: false,
    });
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '' });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    chartRef.current = chart;
    seriesRef.current = { price, volume };

    const ro = new ResizeObserver(() => {
      if (boxRef.current) chart.applyOptions({ width: boxRef.current.clientWidth });
    });
    ro.observe(boxRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      refLineRef.current = null;
    };
  }, []);

  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !Array.isArray(bars)) return;
    s.price.setData(bars.map((b) => ({ time: b.time, value: b.close })));
    s.volume.setData(
      bars.map((b) => ({
        time: b.time,
        value: b.volume,
        color: b.close >= b.open ? 'rgba(16,185,129,0.45)' : 'rgba(239,68,68,0.45)',
      })),
    );
    if (refLineRef.current) {
      s.price.removePriceLine(refLineRef.current);
      refLineRef.current = null;
    }
    if (refPrice) {
      refLineRef.current = s.price.createPriceLine({
        price: refPrice,
        color: COLORS.ref,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'TC',
      });
    }
    chartRef.current?.timeScale().fitContent();
  }, [bars, refPrice]);

  return <div ref={boxRef} className="lq-chart" />;
}

export default function LiveQuote({ symbol }) {
  const [quote, setQuote] = useState(null);
  const [market, setMarket] = useState(null);
  const [intraday, setIntraday] = useState(null);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  // Bảng giá: tải ngay, sau đó 10 giây/lần khi đang trong giờ giao dịch
  useEffect(() => {
    let alive = true;
    let timer = null;
    const load = async () => {
      try {
        const res = await fetchRealtimeQuoteApi(symbol);
        if (!alive) return;
        setQuote(res.quotes?.[symbol] || null);
        setMarket(res.market || null);
        setError(res.quotes?.[symbol] ? null : `Không có dữ liệu bảng giá cho ${symbol}`);
        setUpdatedAt(new Date());
        if (res.market?.live) timer = setTimeout(load, QUOTE_POLL_MS);
      } catch (err) {
        if (!alive) return;
        setError(err.message);
        timer = setTimeout(load, QUOTE_POLL_MS * 3);
      }
    };
    load();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [symbol]);

  // Nến 1 phút: tải ngay, sau đó 60 giây/lần khi đang trong giờ giao dịch
  useEffect(() => {
    let alive = true;
    let timer = null;
    const load = async () => {
      try {
        const res = await fetchIntradayApi(symbol, '1');
        if (!alive) return;
        setIntraday(res);
        if (res.market?.live) timer = setTimeout(load, INTRADAY_POLL_MS);
      } catch {
        if (alive) timer = setTimeout(load, INTRADAY_POLL_MS * 2);
      }
    };
    load();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [symbol]);

  const q = quote;
  const price = q?.price ?? null;
  const shown = price ?? q?.ref ?? null;
  const color = priceColor(price, q);
  const sessionLabel = q?.session ? SESSION_LABELS[String(q.session).toUpperCase()] || q.session : null;
  const lastMatch = fmtTime(q?.last_update);
  const roomPct = q?.foreign_total_room ? (q.foreign_room / q.foreign_total_room) * 100 : null;
  const rows = [0, 1, 2];

  return (
    <div className="glass-panel live-quote">
      <div className="lq-header">
        <div className="lq-title">
          <Radio size={16} className={market?.live ? 'lq-live-dot' : ''} />
          <span>Bảng giá trực tiếp · {symbol}</span>
          {q?.exchange && <span className="lq-tag">{q.exchange}</span>}
          {q?.short_name && <span className="lq-name">{q.short_name}</span>}
        </div>
        <div className="lq-status">
          {market && <span className={`lq-tag ${market.live ? 'lq-tag-live' : ''}`}>{market.label}</span>}
          {sessionLabel && <span className="lq-tag">{sessionLabel}</span>}
          {lastMatch && <span>Khớp lúc {lastMatch}</span>}
          {updatedAt && <span>· tải lúc {updatedAt.toLocaleTimeString('vi-VN')}</span>}
        </div>
      </div>

      {error && !q && <p className="lq-error">{error}</p>}

      {q && (
        <div className="lq-body">
          <div className="lq-price-block">
            <div className="lq-price" style={{ color }}>{fmtPrice(shown)}</div>
            <div className="lq-change" style={{ color }}>
              {q.change == null
                ? 'Chưa có lệnh khớp'
                : `${q.change > 0 ? '+' : ''}${fmtPrice(q.change)} (${q.change_pct > 0 ? '+' : ''}${fmtPrice(q.change_pct)}%)`}
            </div>
            <div className="lq-refs">
              <span>Trần <b style={{ color: COLORS.ceiling }}>{fmtPrice(q.ceiling)}</b></span>
              <span>TC <b style={{ color: COLORS.ref }}>{fmtPrice(q.ref)}</b></span>
              <span>Sàn <b style={{ color: COLORS.floor }}>{fmtPrice(q.floor)}</b></span>
            </div>
            <div className="lq-stats">
              <span>Mở cửa</span><b style={{ color: priceColor(q.open, q) }}>{fmtPrice(q.open)}</b>
              <span>Cao nhất</span><b style={{ color: priceColor(q.high, q) }}>{fmtPrice(q.high)}</b>
              <span>Thấp nhất</span><b style={{ color: priceColor(q.low, q) }}>{fmtPrice(q.low)}</b>
              <span>Giá TB</span><b>{fmtPrice(q.avg)}</b>
              <span>Tổng KL</span><b>{fmtInt(q.volume)}</b>
              <span>Tổng GT</span><b>{fmtBn(q.value_bn)}</b>
            </div>
          </div>

          <div className="lq-book">
            <table>
              <thead>
                <tr><th colSpan={2}>Dư mua</th><th colSpan={2}>Dư bán</th></tr>
                <tr><th>KL</th><th>Giá</th><th>Giá</th><th>KL</th></tr>
              </thead>
              <tbody>
                {rows.map((i) => {
                  const b = q.bid?.[i];
                  const a = q.ask?.[i];
                  return (
                    <tr key={i}>
                      <td>{b ? fmtInt(b.volume) : ''}</td>
                      <td style={{ color: priceColor(b?.price, q) }}>{b ? fmtPrice(b.price) : ''}</td>
                      <td style={{ color: priceColor(a?.price, q) }}>{a ? fmtPrice(a.price) : ''}</td>
                      <td>{a ? fmtInt(a.volume) : ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="lq-foreign">
              <div className="lq-foreign-title">Khối ngoại trong phiên</div>
              <div className="lq-stats">
                <span>Mua</span><b>{fmtBn(q.foreign_buy_bn)} <small>({fmtInt(q.foreign_buy_vol)} cp)</small></b>
                <span>Bán</span><b>{fmtBn(q.foreign_sell_bn)} <small>({fmtInt(q.foreign_sell_vol)} cp)</small></b>
                <span>Ròng</span>
                <b className={q.foreign_net_bn > 0 ? 'up-color' : q.foreign_net_bn < 0 ? 'down-color' : ''}>
                  {fmtBn(q.foreign_net_bn, true)}
                </b>
                <span>Room còn</span>
                <b>
                  {fmtInt(q.foreign_room)} cp
                  {roomPct != null && (
                    <small> ({roomPct.toLocaleString('vi-VN', { maximumFractionDigits: 1 })}% hạn mức)</small>
                  )}
                </b>
              </div>
            </div>
          </div>
        </div>
      )}

      {intraday?.bars?.length > 0 && (
        <>
          <div className="lq-chart-title">
            Diễn biến trong phiên {intraday.date} (nến 1 phút, nguồn {intraday.source})
          </div>
          <IntradayChart bars={intraday.bars} refPrice={q?.ref} />
        </>
      )}

      <p className="lq-note">
        Nguồn: bảng giá Vietcap và biểu đồ DNSE / VNDirect / SSI iBoard. Đây là API công khai không chính thức, có thể trễ
        vài giây hoặc ngừng bất cứ lúc nào. Ngoài giờ giao dịch hiển thị số liệu phiên gần nhất. Giá theo nghìn đồng.
      </p>
    </div>
  );
}
