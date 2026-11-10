import React from 'react';
import { Crown, Swords, ShieldAlert, ScrollText, CheckCircle2, Clock } from 'lucide-react';

/**
 * ExecutiveSummaryBanner - Khung Tóm Tắt Hành Động 3 Dòng Do Minh Chủ Võ Lâm Ký Duyệt (R4)
 *
 * Cấu trúc 3 dòng chuẩn quân cơ:
 * - Dòng 1 (Hành động): Khuyến nghị Mua thăm dò / Quan sát / Bán, vùng giá gom, tỷ trọng danh mục (<=25%), khung giờ vàng (13h45 - 14h25).
 * - Dòng 2 (Bộ 3 Chốt Chặn): Price-Stop nới ATR an toàn, Thesis-Stop điều kiện bẻ gãy luận điểm, Time-Stop thời hạn T+10.
 * - Dòng 3 (Quân lệnh Minh Chủ): Lời phê chuẩn tối hậu, tổng kết ý kiến phản biện của Tham Mưu Các và giám định tài chính của Huyết Vũ Lâu.
 */
export default function ExecutiveSummaryBanner({
  executiveSummary,
  report,
  symbol = 'HPG',
  verdict,
  sessionId,
}) {
  const ex = executiveSummary || report?.executive_summary || {};
  const tp = report?.trade_plan || {};
  const stops = tp.exit_stops || {};

  // Dòng 1: Hành động tác chiến
  const actionLine =
    ex.action_line ||
    (ex.summary_lines && ex.summary_lines[0]) ||
    `QUAN SÁT / MUA THĂM DÒ: Giải ngân ${tp.max_nav_pct || 20}% NAV tại vùng [${tp.entry_low || 27.8} – ${tp.entry_high || 28.5}] trong khung giờ vàng 13h45–14h25 (sau khi hấp thụ xong hàng T+2,5).`;

  // Dòng 2: Bộ 3 chốt chặn bảo vệ vốn
  const defenseStopsLine =
    ex.defense_stops_line ||
    (ex.summary_lines && ex.summary_lines[1]) ||
    `BỘ 3 CHỐT CHẶN: Price-Stop ${tp.stop_loss || 26.6} (nới đệm ATR an toàn) · Thesis-Stop ${stops.thesis_stop?.condition || 'Gãy nền hỗ trợ kèm vol > 1.5x TB20 hoặc khối ngoại xả ròng'} · Time-Stop ${stops.time_stop?.condition || 'Sau T+10 phiên không bứt phá thì chủ động hạ 50% tỷ trọng'}.`;

  // Dòng 3: Quân lệnh Minh Chủ
  const directiveLine =
    ex.directive_line ||
    (ex.summary_lines && ex.summary_lines[2]) ||
    `QUÂN LỆNH MINH CHỦ: Huyết Vũ Lâu xác nhận dòng tiền CFO dương & không vướng bẫy GDKHQ; Tham Mưu Các cảnh báo khống chế tỷ trọng ≤ 25% NAV; Minh Chủ Võ Lâm phê chuẩn lệnh tác chiến.`;

  // Phân loại sắc thái hành động
  const isBuy = /mua|tích cực|mở vị thế/i.test(actionLine);
  const isSell = /bán|hạ tỷ trọng|thoát vị thế/i.test(actionLine);
  const actionBadge = isBuy ? 'MUA THĂM DÒ' : isSell ? 'HẠ VỊ THẾ' : 'QUAN SÁT CẨN TRỌNG';
  const actionBadgeColor = isBuy ? '#00c076' : isSell ? '#ff3b30' : '#ffb800';

  return (
    <div className="ws-exec-banner">
      {/* Header bar với dấu ấn hoàng kim của Minh Chủ */}
      <div className="ws-exec-header">
        <div className="ws-exec-title-group">
          <div className="ws-exec-icon-box">
            <Crown size={20} className="ws-exec-crown-icon" />
          </div>
          <div>
            <div className="ws-exec-title">
              QUÂN CƠ NGHỊ QUYẾT — MINH CHỦ VÕ LÂM KÝ DUYỆT
            </div>
            <div className="ws-exec-subtitle">
              Phiên họp Hội Đồng Đa Tác Nhân Phân Cấp · Mã: <strong>{symbol}</strong>
              {sessionId && <span className="ws-exec-session-tag"> · {sessionId}</span>}
            </div>
          </div>
        </div>

        <div className="ws-exec-seal-group">
          <span
            className="ws-exec-action-badge"
            style={{
              borderColor: `${actionBadgeColor}66`,
              color: actionBadgeColor,
              backgroundColor: `${actionBadgeColor}18`,
            }}
          >
            {actionBadge}
          </span>
          <div className="ws-exec-seal">
            <ScrollText size={13} />
            <span>TRIỆN ẤN MINH CHỦ</span>
          </div>
        </div>
      </div>

      {/* 3 Dòng Chỉ Thị Quân Cơ */}
      <div className="ws-exec-lines">
        {/* Dòng 1: Hành động */}
        <div className="ws-exec-line ws-exec-line-action">
          <div className="ws-exec-line-tag">
            <Swords size={15} />
            <span>DÒNG 1: HÀNH ĐỘNG</span>
          </div>
          <div className="ws-exec-line-content">
            <div className="ws-exec-line-text">{actionLine}</div>
            <div className="ws-exec-chips">
              <span className="ws-exec-chip ws-chip-gold">
                <Clock size={11} /> Giờ vàng: 13h45 – 14h25
              </span>
              <span className="ws-exec-chip ws-chip-green">
                Tỷ trọng tối đa: ≤ 25% NAV
              </span>
              <span className="ws-exec-chip ws-chip-blue">
                Tuân thủ nến đóng phiên T+2,5
              </span>
            </div>
          </div>
        </div>

        {/* Dòng 2: Bộ 3 Chốt Chặn */}
        <div className="ws-exec-line ws-exec-line-defense">
          <div className="ws-exec-line-tag">
            <ShieldAlert size={15} />
            <span>DÒNG 2: 3 CHỐT CHẶN</span>
          </div>
          <div className="ws-exec-line-content">
            <div className="ws-exec-line-text">{defenseStopsLine}</div>
            <div className="ws-exec-chips">
              <span className="ws-exec-chip ws-chip-red">
                Price-Stop: Đệm ATR an toàn
              </span>
              <span className="ws-exec-chip ws-chip-amber">
                Thesis-Stop: Bẻ gãy luận điểm
              </span>
              <span className="ws-exec-chip ws-chip-purple">
                Time-Stop: Ngưỡng thời hạn T+10
              </span>
            </div>
          </div>
        </div>

        {/* Dòng 3: Quân lệnh Minh Chủ */}
        <div className="ws-exec-line ws-exec-line-directive">
          <div className="ws-exec-line-tag">
            <Crown size={15} />
            <span>DÒNG 3: QUÂN LỆNH</span>
          </div>
          <div className="ws-exec-line-content">
            <div className="ws-exec-line-text">{directiveLine}</div>
            <div className="ws-exec-chips">
              <span className="ws-exec-chip ws-chip-cyan">
                <CheckCircle2 size={11} /> Huyết Vũ Lâu: Giám định CFO & GDKHQ
              </span>
              <span className="ws-exec-chip ws-chip-orange">
                Tham Mưu Các: Phản biện vai ác & Siết rủi ro
              </span>
              <span className="ws-exec-chip ws-chip-gold">
                Minh Chủ: Phán quyết tối hậu
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
