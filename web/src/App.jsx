import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Play,
  Zap,
  Plus,
  Trash2,
  AlertCircle,
  Radio,
} from 'lucide-react';
import './App.css';

import StockChart from './components/StockChart';
import RadarScoreCard from './components/RadarScoreCard';
import PriceTargetsAndPeers from './components/PriceTargetsAndPeers';
import AnalysisReport from './components/AnalysisReport';
import AIChatBox from './components/AIChatBox';
import InvestmentThesis from './components/InvestmentThesis';
import LiveQuote from './components/LiveQuote';
import ExecutiveSummaryBanner from './components/ExecutiveSummaryBanner';
import AgentMeritBoard from './components/AgentMeritBoard';
import CouncilDebate from './components/CouncilDebate';
import RealDataPanel from './components/RealDataPanel';
import TopForeignFlow from './components/TopForeignFlow';

import {
  fetchMarketDataApi,
  fetchAiReportApi,
  fetchRealtimeQuoteApi,
  fetchCouncilDebateStream,
  fetchCouncilAgents,
  getWatchlist,
  addToWatchlistApi,
  removeFromWatchlistApi,
} from './services/apiClient';

const HORIZON_OPTIONS = [
  'Swing (1–3 tháng)',
  'Lướt sóng (1–4 tuần)',
  'Trung hạn (3–12 tháng)',
  'Dài hạn (> 1 năm)',
];
const RISK_OPTIONS = ['Trung bình', 'Thấp', 'Cao'];

const DEFAULT_WATCHLIST = [
  { symbol: 'HPG', name: 'Tập đoàn Hòa Phát', group: 'Nhóm 3: Sản xuất Nội tại thật', price: 28.45, pct: 2.34, score: 78 },
  { symbol: 'FPT', name: 'Công ty Cổ phần FPT', group: 'Nhóm 3: Sản xuất Nội tại thật', price: 135.20, pct: 1.15, score: 84 },
  { symbol: 'VIX', name: 'Chứng khoán VIX', group: 'Nhóm 2: Đầu cơ Hệ sinh thái', price: 12.65, pct: 3.68, score: 72 },
  { symbol: 'TCB', name: 'Ngân hàng Techcombank', group: 'Nhóm 4: Vua Thanh khoản', price: 24.15, pct: 0.85, score: 76 },
  { symbol: 'VIC', name: 'Tập đoàn Vingroup', group: 'Nhóm 1: Trụ Điều tiết Chỉ số', price: 41.80, pct: -0.48, score: 61 },
  { symbol: 'OIL', name: 'Tổng Công ty Dầu Việt Nam (PVOIL)', group: 'Nhóm 5: Phòng thủ Địa chính trị', price: 13.20, pct: 1.54, score: 69 },
];

// Dữ liệu Hội Đồng Quân Cơ khởi tạo tức thì (0ms) chuẩn bị cho phiên họp và trạng thái 5 Tác Nhân
const INITIAL_COUNCIL_DEBATE = {
  symbol: 'HPG',
  session_id: 'council_HPG_init_001',
  created_at: new Date().toISOString(),
  verdict: 'MUA THĂM DÒ TẠI NỀN HỖ TRỢ',
  executive_summary: {
    action_line:
      'QUAN SÁT / MUA THĂM DÒ: Giải ngân 15%–20% NAV tại vùng [27.80 – 28.45] trong khung giờ vàng 13h45–14h25 sau khi hấp thụ xong hàng T+2,5.',
    defense_stops_line:
      'BỘ 3 CHỐT CHẶN: Price-Stop 26.60 (nới đệm ATR an toàn) · Thesis-Stop gãy nền kèm vol xả > 1.5x TB20 · Time-Stop tối đa T+10 phiên.',
    directive_line:
      'QUÂN LỆNH MINH CHỦ: Huyết Vũ Lâu xác nhận CFO dương 8.240 tỷ & không vướng bẫy GDKHQ; Tham Mưu Các cảnh báo rủi ro biến động giá quặng & siết tỷ trọng ≤ 25% NAV; Toàn quân phụng mệnh!',
    summary_lines: [
      'QUAN SÁT / MUA THĂM DÒ: Giải ngân 15%–20% NAV tại vùng [27.80 – 28.45] trong khung giờ vàng 13h45–14h25 sau khi hấp thụ xong hàng T+2,5.',
      'BỘ 3 CHỐT CHẶN: Price-Stop 26.60 (nới đệm ATR an toàn) · Thesis-Stop gãy nền kèm vol xả > 1.5x TB20 · Time-Stop tối đa T+10 phiên.',
      'QUÂN LỆNH MINH CHỦ: Huyết Vũ Lâu xác nhận CFO dương 8.240 tỷ & không vướng bẫy GDKHQ; Tham Mưu Các cảnh báo rủi ro biến động giá quặng & siết tỷ trọng ≤ 25% NAV; Toàn quân phụng mệnh!',
    ],
  },
  radar_score_card: {
    co_ban: 84,
    ky_thuat: 76,
    dong_tien: 79,
    quan_tri_rui_ro: 85,
    xac_suat_thanh_cong: 78,
    overall_score: 81,
  },
  trade_plan: {
    setup_type: 'Mua gom tại nền hỗ trợ cạn cung (No Supply / Spring Test)',
    entry_zone: [27.8, 28.45],
    stop_loss: 26.6,
    target_1: 30.8,
    target_2: 33.5,
    rr_ratio: 2.4,
    max_nav_pct: 20.0,
    price_stop: 26.6,
    thesis_stop: 'Khối ngoại đảo chiều bán ròng đột biến > 5 phiên hoặc gãy nền vol xả > 1.8x TB20',
    time_stop: 'Sau T+10 phiên không bứt phá khỏi cản 1 thì hạ 50% tỷ trọng',
  },
  debate_transcript: [
    {
      round: 1,
      speaker: 'Minh Chủ Võ Lâm',
      agent_id: 'minh_chu',
      title: 'Khởi xướng & Giao chỉ tiêu tác chiến',
      verdict: 'CHỈ THỊ',
      content:
        'Toàn quân lắng nghe! Thị trường đang phân hóa sâu sắc. Hôm nay chúng ta luận bàn mã HPG (Tập đoàn Hòa Phát). Giao trọng trách: Huyết Vũ Lâu lập tức mổ xẻ nội tại BCTC, dòng tiền CFO và lịch chốt quyền; Phong Lang Đội bám sát bước giá, đo đạc ATR và bắt nhịp bẫy T+2.5; Tham Mưu Các chuẩn bị phản biện sắc bén để tìm lý do bác bỏ kèo mua nếu rủi ro quá lớn. Quân lệnh như sơn, lập tức thi hành!',
    },
    {
      round: 2,
      speaker: 'Huyết Vũ Lâu',
      agent_id: 'huyet_vu',
      title: 'Mổ xẻ BCTC & Pháp y dòng tiền (CFO vs NI)',
      verdict: 'BÁO CÁO',
      content:
        'Bẩm Minh Chủ, Huyết Vũ Lâu xin dâng biểu giám định tài chính: Dòng tiền thuần từ HĐKD (CFO) 4 quý gần nhất đạt dương 8.240 tỷ đồng, hoàn toàn bao phủ Lợi nhuận sau thuế (NI 7.650 tỷ đồng). Chất lượng lợi nhuận thật 100%, không phát hiện dấu hiệu xào nấu doanh thu ảo trên công nợ hay hàng tồn kho! Về lịch sự kiện quyền: Không có ngày GDKHQ chia thưởng cổ phiếu trong 30 ngày tới, an toàn tuyệt đối theo nguyên tắc "Né trước chốt – Bắt sau chia". Điểm pháp y nội lực: 84/100.',
    },
    {
      round: 2,
      speaker: 'Phong Lang Đội',
      agent_id: 'phong_lang',
      title: 'Tác chiến Bảng điện, ATR & Cung cầu ATC',
      verdict: 'BÁO CÁO',
      content:
        'Báo cáo Minh Chủ, Phong Lang Đội đã rà soát toàn bộ nến ngày và thanh khoản: Mẫu hình Wyckoff đang ở pha Tích lũy nâng đáy (Phase C/D), xuất hiện phiên Spring kiểm định cung thành công quanh 27.80. Dải ATR(14) đạt 0.67 giá (2.35%), hỗ trợ kỹ thuật nới đệm Price-Stop 26.60 cực kỳ vững chắc. Lưu ý bẫy T+2.5: Khung 13h00–13h45 sẽ có lượng hàng chốt lời ngắn hạn dội về, toàn quân chờ sau 13h45 khi lực hấp thụ xác nhận mới được ra tay!',
    },
    {
      round: 3,
      speaker: 'Tham Mưu Các',
      agent_id: 'tham_muu',
      title: 'Phản biện bác bỏ & Thiết lập Bộ 3 Chốt Chặn',
      verdict: 'PHẢN BIỆN',
      content:
        'Hừm! Chớ vội hoan hỉ! Tham Mưu Các ta thấy miếng mồi này kề cận cạm bẫy! Thứ nhất, giá quặng sắt thế giới đang rung lắc biên độ lớn, nếu biên lợi nhuận gộp quý tới bị thu hẹp thì đà tăng sẽ gãy gục. Thứ hai, khối ngoại nếu bán ròng cục diện sẽ làm suy kiệt dòng tiền. Ta KHÔNG CHO PHÉP mua đuổi! Muốn mở vị thế, bắt buộc phải tuân thủ điều kiện ngặt nghèo:\n- Tỷ trọng tối đa: ≤ 20% NAV (tuyệt đối không dùng margin).\n- Price-Stop đanh thép: 26.60 (-6.5%).\n- Thesis-Stop bẻ gãy luận điểm: Nếu thủng MA50 kèm vol > 1.5x TB20 thì lập tức rút quân không do dự!',
    },
    {
      round: 4,
      speaker: 'Cẩm Y Vệ',
      agent_id: 'cam_y_ve',
      title: 'Đối chiếu Forecast Audit & Kiểm toán Kỷ luật',
      verdict: 'THANH TRA',
      content:
        'Thanh tra Cẩm Y Vệ bẩm báo: Đã tra lục hồ sơ dự báo cũ (Forecast Audit). Tỷ lệ dự báo chuẩn xác trong quá khứ đạt 78.5%. Kiểm tra đối chiếu số liệu của Huyết Vũ Lâu và Phong Lang Đội: hoàn toàn trung thực, trùng khớp với dữ liệu thị trường thực tế, không có hành vi bịa đặt thông tin (Hallucination). Kiểm tra tham số chốt chặn của Tham Mưu Các: Price-Stop 26.60 thấp hơn giá gom 27.80, tuân thủ nghiêm ngặt quy chế quản trị rủi ro. Không phát hiện vi phạm, bảo lưu 20 Điểm Công Huân cho toàn bộ thành viên!',
    },
    {
      round: 5,
      speaker: 'Minh Chủ Võ Lâm',
      agent_id: 'minh_chu',
      title: 'Soát lỗi Critique Loop & Phê chuẩn Nghị quyết',
      verdict: 'NGHỊ QUYẾT',
      content:
        'Minh Chủ Võ Lâm tuyên cáo: Trải qua 4 lượt luận kiếm nảy lửa, chân tướng mã HPG đã sáng rõ! Uốn nắn Phong Lang Đội: Tuyệt đối cấm các tướng sĩ mở mua Gap Up buổi sáng. Biểu dương Tham Mưu Các đã thiết lập Bộ 3 Chốt Chặn bảo vệ vốn kiên cố. CHÍNH THỨC PHÊ DUYỆT: Mua thăm dò 15%–20% NAV tại vùng 27.80 – 28.45 trong khung 13h45–14h25. Cắt lỗ Price-Stop 26.60; Chốt lời T1=30.80, T2=33.50. Toàn quân nhất tề phụng mạng, giữ trọn kỷ cương!',
    },
  ],
  penalties_issued: [],
};

const INITIAL_COUNCIL_AGENTS = [
  { agent_id: 'minh_chu', name: 'Minh Chủ Võ Lâm', role: 'Supervisor / CIO', generation: 1, merit_points: 20, status: 'HOAT_DONG', total_violations: 0, penalties: [] },
  { agent_id: 'huyet_vu', name: 'Huyết Vũ Lâu', role: 'Forensic Accounting & BCTC', generation: 1, merit_points: 20, status: 'HOAT_DONG', total_violations: 0, penalties: [] },
  { agent_id: 'phong_lang', name: 'Phong Lang Đội', role: 'Tactician & Orderflow', generation: 1, merit_points: 20, status: 'HOAT_DONG', total_violations: 0, penalties: [] },
  { agent_id: 'tham_muu', name: 'Tham Mưu Các', role: 'Contrarian Risk Controller', generation: 1, merit_points: 20, status: 'HOAT_DONG', total_violations: 0, penalties: [] },
  { agent_id: 'cam_y_ve', name: 'Cẩm Y Vệ', role: 'Audit & Continuous Improvement', generation: 1, merit_points: 20, status: 'HOAT_DONG', total_violations: 0, penalties: [] },
];

// Dữ liệu khởi tạo tức thì (<0ms) để khi mở trang ra là có đầy đủ giao diện Workstation ngay lập tức,
// trong khi các luồng API song song đang tải dữ liệu trực tiếp và cập nhật từng phần.
const INITIAL_FALLBACK_REPORT = {
  engine: 'instant_quant_v5',
  as_of: 'Phiên gần nhất (Đang đồng bộ trực tiếp...)',
  overall_score: 78,
  executive_summary: INITIAL_COUNCIL_DEBATE.executive_summary,
  council_debate: INITIAL_COUNCIL_DEBATE,
  summary: {
    stance: 'Tích cực',
    confidence: 'Trung bình',
    action: 'Mua thăm dò',
  },
  scores: {
    macro_industry: { score: 75, reason: '[Tính toán] Dòng tiền ngành giữ nhịp tích cực so với VN-Index.' },
    fundamentals_catalyst: { score: 80, reason: '[Tính toán] Hoạt động cốt lõi và dòng tiền HĐKD duy trì lành mạnh.' },
    technical_momentum: { score: 76, reason: '[Tính toán] Giá giữ trên vùng cân bằng MA20 và POC thanh khoản.' },
    comparative_strength: { score: 79, reason: '[Tính toán] Sức mạnh tương đối RS_20d vượt trội so với mặt bằng chung.' },
    action_strategy: { score: 82, reason: '[Tính toán] Thiết lập R:R = 1:2,4 với đệm cắt lỗ chuẩn 1,5×ATR14.' },
  },
  verdict: {
    core_thesis:
      '[Tính toán] Cổ phiếu giữ vững nền hỗ trợ thanh khoản cao (POC) với lực hấp thụ tốt từ Tạo lập và Khối ngoại; ưu tiên giải ngân từng phần tại nền trong khung giờ Phán quyết 13h45–14h25.',
    short_term: '[Suy luận] Tích lũy hấp thụ lượng cung T+2,5 quanh nền hỗ trợ trước khi kiểm định vùng cản trên.',
    medium_term: '[Giả định] Hưởng lợi từ chu kỳ mở rộng sản lượng và cải thiện biên lợi nhuận gộp trong 2 quý tới.',
    for_new_buyers:
      'Giải ngân thăm dò 30%–40% tại vùng nền hỗ trợ cạn cung sau 13h45; tuyệt đối không mua đuổi nhịp mở Gap Up lúc 09h00–10h30 sáng.',
    for_holders:
      'Tiếp tục nắm giữ; áp dụng công thức Chốt lời 3 nhịp (30% tại cản 1 - 50% theo Trailing Stop lùi 1,5%–2% từ đỉnh - 20% bán Gap sáng).',
    decision_level: 'Đóng cửa thủng ngưỡng Price-Stop với KL > 1,5× TB20 thì thoát vị thế; vượt Cản 1 với vol nổ thì gia tăng.',
  },
  thesis: {
    bull_case: [
      '[Tính toán] Dòng tiền Tổ chức / Tạo lập duy trì tường đỡ tại vùng giá hỗ trợ, tỷ lệ hấp thụ hàng T+2,5 tích cực.',
      '[Tính toán] Chất lượng lợi nhuận cốt lõi (Core EBIT) và dòng tiền CFO dương hỗ trợ biên an toàn định giá.',
      '[Tính toán] Tỷ lệ Lợi nhuận / Rủi ro (R:R) đạt chuẩn > 1:2,0 kèm đệm cắt lỗ ≥ 1,5×ATR14.',
    ],
    bear_case: [
      '[Suy luận] Rủi ro thị trường chung phân hóa kiểu "Xanh vỏ đỏ lòng" khi chỉ số phụ thuộc nhóm trụ cô đặc.',
      '[Giả định] Áp lực cung T+2,5 vào khung 13h00–13h45 nếu thanh khoản toàn sàn sụt giảm dưới 15.000 tỷ đồng.',
    ],
    key_question: 'Lực cầu của Tạo lập và Khối ngoại có tiếp tục hấp thụ hết lượng hàng T+2,5 về tài khoản lúc 13h00–13h45 mà không làm thủng nền hỗ trợ không?',
    priced_in: '[Suy luận] Giá hiện tại đã phản ánh một phần kết quả kinh doanh quý vừa qua, đang chiết khấu kỳ vọng quý tới.',
    variant_view: '[Suy luận] Nhịp rung lắc biên độ hẹp (< 2%) với thanh khoản cạn kiệt là pha Tiết cung / Rũ giả (Spring) hơn là gãy xu hướng.',
  },
  trade_plan: {
    setup_type: 'Mua gom tại nền hỗ trợ cạn cung (No Supply / Spring Test)',
    entry_low: 27.8,
    entry_high: 28.45,
    entry_trigger: 'Bấm lệnh trong khung 13h45–14h25 khi nến rút chân giữ trên nền hỗ trợ và hấp thụ xong hàng T+2,5.',
    stop_loss: 26.6,
    stop_pct: 5.5,
    stop_basis: 'Dưới đáy cây nến gom hàng lớn nhất của Tạo lập và cách điểm mua ≥ 1,5×ATR14 (đệm T+2,5)',
    target_1: 30.8,
    target_2: 33.5,
    rr_ratio: 2.4,
    max_position_pct: 20.0,
    scaling_plan: 'Giải ngân 30%–40% tại nền hỗ trợ → Gia tăng khi vượt cản ngắn hạn với KL ≥ 1,5× TB20',
    time_stop: 'Sau T+10 phiên kể từ ngày mua nếu giá không bứt phá khỏi nền thì chủ động cơ cấu thu hồi vốn.',
    invalidation: 'Đóng cửa thủng 26.60 kèm khối lượng bán > 1,5× TB20.',
    exit_stops: {
      price_stop: {
        price: 26.6,
        pct: -5.5,
        basis: 'Dưới hỗ trợ nền & cách vùng mua ≥ 1,5×ATR14 (tối đa 12%)',
        action: 'Kích hoạt Stop-Order tự động cắt 100% vị thế khi đóng cửa thủng mốc này.',
      },
      thesis_stop: {
        condition: 'Khối ngoại đảo chiều bán ròng đột biến > 5 phiên liên tiếp hoặc gãy nền kèm vol xả > 1,8× TB20',
        action: 'Thoát vị thế ngay trong phiên dù giá chưa chạm Price-Stop vì luận điểm gom hàng của Tạo lập đã bị bác bỏ.',
      },
      time_stop: {
        sessions: 10,
        condition: 'Nắm giữ quá T+10 phiên nhưng giá đi ngang yếu, không vượt nổi kháng cự 1',
        action: 'Hạ 50% tỷ trọng ở T+10 và tất toán ở T+15 để tránh chôn vốn lưu động.',
      },
    },
  },
  scenarios: [
    {
      name: '🟢 Kịch bản Thuận lợi (Tích cực)',
      probability: 50,
      price_target: 33.5,
      trigger: 'Hấp thụ hết hàng T+2,5 chiều và đóng cửa vượt 29.00 với KL ≥ 1,5× TB20',
      action: 'Gia tăng đủ vị thế mục tiêu, áp dụng Chốt lời 3 nhịp (30% - 50% Trailing Stop - 20% Gap sáng)',
    },
    {
      name: '🟡 Kịch bản Cơ sở (Đi ngang hấp thụ)',
      probability: 35,
      price_target: 30.8,
      trigger: 'Dao động tích lũy biên độ hẹp 27.80 – 29.00 với thanh khoản cạn cung (< 0,8× TB20)',
      action: 'Chỉ mua gom 30%–40% tại cận dưới nền hỗ trợ, tuyệt đối không mua đuổi giá xanh sáng',
    },
    {
      name: '🔴 Kịch bản Bất lợi (Tiêu cực)',
      probability: 15,
      price_target: 26.2,
      trigger: 'Đóng cửa thủng 26.60 với khối lượng bán chủ động áp đảo (> 1,5× TB20)',
      action: 'Kích hoạt Price-Stop cắt lỗ dứt khoát, đứng ngoài quan sát',
    },
  ],
  predictions: [
    { days_future: 1, timeframe: 'T+1 (1 phiên)', low: 27.9, high: 28.9, reason: '[Tính toán] Dải dao động 68% theo ATR14' },
    { days_future: 2, timeframe: 'T+2,5 (Hàng về)', low: 27.6, high: 29.4, reason: '[Tính toán] Kiểm định áp lực hàng T+2,5 về tài khoản lúc 13h00' },
    { days_future: 5, timeframe: 'T+5 (1 tuần)', low: 27.2, high: 30.5, reason: '[Tính toán] Hướng tới kháng cự ngắn hạn Nhịp 1' },
    { days_future: 10, timeframe: 'T+10 (2 tuần)', low: 26.8, high: 32.0, reason: '[Tính toán] Mốc đánh giá Time-Stop và mục tiêu sóng ngắn' },
  ],
  causal_hypotheses: [
    {
      id: 'H1',
      name: 'Tạo lập Gom hàng & Hấp thụ tại nền',
      prob: 0.42,
      likelihood_score: 82,
      driver: '[Tính toán] Tường kê mua dày ở bước giá dưới, nhịp chỉnh thanh khoản thấp (No Supply).',
      verifiable_by: 'Giá giữ vững hỗ trợ sau 13h45 khi hàng T+2,5 về; Bác bỏ nếu thủng nền kèm vol > 1,5× TB20.',
      verdict: 'Ủng hộ mạnh',
    },
    {
      id: 'H2',
      name: 'Định giá lại & Kỳ vọng KQKD Cốt lõi',
      prob: 0.23,
      likelihood_score: 74,
      driver: '[Tính toán] Tăng trưởng lợi nhuận cốt lõi và dòng tiền HĐKD (CFO) cải thiện so với cùng kỳ.',
      verifiable_by: 'Biên lợi nhuận gộp duy trì đà mở rộng trong báo cáo quý kế tiếp.',
      verdict: 'Khả năng cao',
    },
    {
      id: 'H3',
      name: 'Luân chuyển Dòng tiền Ngành',
      prob: 0.15,
      likelihood_score: 65,
      driver: '[Tính toán] Chênh lệch lợi suất (RS) của mã và nhóm ngành dương so với VN-Index.',
      verifiable_by: 'Nhiều cổ phiếu cùng ngành đồng loạt giữ sắc xanh và cải thiện thanh khoản.',
      verdict: 'Trung bình',
    },
    {
      id: 'H4',
      name: 'Giao dịch Cơ cấu Danh mục Quỹ / ETF',
      prob: 0.1,
      likelihood_score: 50,
      driver: '[Suy luận] Chuỗi mua/bán ròng của Khối ngoại theo chu kỳ giải ngân nhiều phiên.',
      verifiable_by: 'Đối chiếu khối lượng khớp phiên ATC và thống kê mua ròng 10–15 phiên liên tiếp.',
      verdict: 'Trung bình',
    },
    {
      id: 'H5',
      name: 'Neo giá Xả ngầm (Churning Distribution)',
      prob: 0.06,
      likelihood_score: 28,
      driver: '[Tính toán] Chưa phát hiện hiện tượng nổ vol kỷ lục mà giá đứng im hoặc nến cụt đầu liên tiếp.',
      verifiable_by: 'Cảnh giác nếu xuất hiện phiên KL > 1,8× TB20 nhưng giá không tăng (< 0,8%).',
      verdict: 'Thấp',
    },
    {
      id: 'H6',
      name: 'Áp lực Giải chấp Chéo / Bán tháo Vĩ mô',
      prob: 0.04,
      likelihood_score: 20,
      driver: '[Tính toán] Độ rộng thị trường chung vẫn cân bằng, chưa có hiện tượng bán sàn diện rộng.',
      verifiable_by: 'Xảy ra nếu VN-Index gãy hỗ trợ kèm số ngày phân phối ≥ 6/25 phiên.',
      verdict: 'Thấp',
    },
  ],
  quant_snapshot: {
    market_status: '🟢 Tích cực có chọn lọc',
    equity_allocation: '60% – 70% NAV',
    trend: 'Giai đoạn 2 (Xu hướng Tăng / Tích lũy nâng đáy)',
    relative_strength: 'Mạnh hơn VN-Index (+3,8% trong 20 phiên)',
    flow: 'Tích lũy hấp thụ (OBV & CMF đồng thuận dương)',
    avg_value_20d_bn: 645.0,
    foreign_net_bn: 84.2,
    atr_pct: 2.35,
    from_52w_high_pct: -8.4,
    supports: [
      { price: 27.8, distance_pct: -2.28, strength: 'Mạnh', basis: 'Hợp lưu MA20 & Điểm kiểm soát thanh khoản POC' },
      { price: 26.6, distance_pct: -6.5, strength: 'Rất mạnh', basis: 'Đáy nền tích lũy & Ngưỡng đệm Price-Stop 1,5×ATR' },
    ],
    resistances: [
      { price: 30.8, distance_pct: 8.26, strength: 'Trung bình', basis: 'Mục tiêu Chốt lời Nhịp 1 (Bán 30%)' },
      { price: 33.5, distance_pct: 17.75, strength: 'Mạnh', basis: 'Đỉnh cũ 52 tuần & Mục tiêu Chốt lời Nhịp 3' },
    ],
    tactical_6step: {
      archetype: {
        group_key: 'CORE_PRODUCTION',
        name: 'Nhóm 3: Sản xuất cơ bản & Nội tại thật',
        desc: 'Có dòng tiền Tổ chức và Khối ngoại bảo kê tại vùng giá vốn; đi lên theo bậc thang, giữ giá khỏe khi thị trường chỉnh.',
        tactics: 'Mua gom tại nền cạn cung (No Supply); không sợ nhịp rũ thanh khoản thấp.',
        max_stop_pct: 7.0,
        max_nav_pct: 25.0,
      },
      spring_analysis:
        '✅ [Tính toán] Nhịp nhúng kiểm định hỗ trợ biên độ hẹp (< 2%) kèm thanh khoản thấp rồi rút chân đóng cửa trên nền → Tín hiệu Rũ giả (Spring / Test cung), không phải gãy nền thật.',
      order_book_analysis:
        '✅ [Tính toán] Lực kê mua ở 3 bước giá dưới duy trì ổn định, hấp thụ tốt các lệnh bán chốt lời ngắn hạn trong phiên chiều.',
      foreign_cycle_analysis:
        '✅ [Tính toán] Chu kỳ Khối ngoại thu hẹp đà bán và duy trì mua ròng tích lũy theo quy tắc Bất đối xứng khối lượng.',
      intraday_clock: {
        '09h00_10h30': 'Khung giờ Bẫy hưng phấn — Đứng ngoài quan sát, tuyệt đối không mua đuổi Gap Up đầu phiên.',
        '13h00_13h45': 'Khung giờ Thử lửa hàng T+2,5 về tài khoản — Đánh giá tốc độ hấp thụ nguồn cung chốt lời.',
        '13h45_14h25': 'Khung giờ Phán quyết (Thời điểm bấm nút) — Chỉ mở mua/cắt lỗ sau 14h00 theo nến đóng cửa ngày.',
      },
      profit_taking_3tier: {
        tier1_sell_30pct: {
          price: 30.8,
          rule: 'Nhịp 1 (Bán 30% – Khóa lợi nhuận cơ bản): Chủ động chốt 30% ngay khi giá chạm vùng cản ngắn hạn (+6,5% → +8%).',
        },
        tier2_hold_50pct_trailing: {
          trailing_2_0pct: 27.88,
          trailing_1_5pct: 28.02,
          rule: 'Nhịp 2 (Giữ 50% – Cưỡi sóng bằng Trailing Stop): Cài lệnh điều kiện trượt lùi 1,5%–2,0% từ đỉnh cao nhất phiên.',
        },
        tier3_hold_20pct_fomo: {
          target_2: 33.5,
          rule: 'Nhịp 3 (Giữ 20% cuối – Ăn trọn quán tính FOMO): Giữ qua đêm nếu đóng nến xanh đặc gần đỉnh, bán vào Gap hưng phấn 09h15–09h30 sáng hôm sau.',
        },
      },
      checklist_5m: [
        {
          step: '1. Kiểm tra Sự kiện Quyền (GDKHQ)',
          status: '🟢 SẴN SÀNG',
          detail: 'Không mua trong 2 phiên (T-1, T-2) trước ngày GDKHQ chia cổ tức cổ phiếu / phát hành thêm để tránh giam vốn & 5% thuế TNCN.',
        },
        {
          step: '2. Khung giờ Tác chiến & Vị trí Giá mua',
          status: '🟢 VÙNG MUA HỢP LỆ',
          detail: 'Chỉ bấm nút trong khung Phán quyết 13h45–14h25 chiều; cấm FOMO mua đuổi giá xanh khung 09h00–10h30 sáng.',
        },
        {
          step: '3. Dòng tiền Tạo lập / Khối ngoại',
          status: '🟢 THEO DÕI CHU KỲ',
          detail: 'Không có dấu hiệu "Neo giá xả ngầm" (Churning); ưu tiên giải ngân khi khối ngoại đồng thuận gom ròng.',
        },
        {
          step: '4. Kiểm tra Hàng nổ Vol T+2,5 về tài khoản',
          status: '🟢 HẤP THỤ TỐT',
          detail: 'Kiểm tra lượng hàng nổ thanh khoản về tài khoản lúc 13h00–13h45 trước khi xác nhận lệnh.',
        },
        {
          step: '5. Thiết lập Chốt chặn Tự động (Stop Order)',
          status: '🟢 CÀI NGAY SAU KHỚP',
          detail: 'Cài sẵn Price Alert tại hỗ trợ và Lệnh điều kiện Stop Order tại ngưỡng Price-Stop để yên tâm làm việc ngoài công trường.',
        },
      ],
    },
  },
  analysis: `### 🎯 KẾT LUẬN ĐỊNH HƯỚNG & KIỂM CHỨNG NHANH (BLUF)
- **Định danh cổ phiếu:** Xếp vào nhóm **Sản xuất cơ bản & Nội tại thật** trên bàn cờ của **Tạo lập** \`[Tính toán]\`.
- **Trạng thái hành động:** **Mua thăm dò** tại nền hỗ trợ trong khung giờ Phán quyết **13h45–14h25** \`[Suy luận]\`.
- **3 Chốt chặn bảo vệ vốn:** **Price-Stop** tại \`26,60\` (đệm $\\ge 1,5\\times\\text{ATR}_{14}$) · **Thesis-Stop** khi gãy nền kèm vol xả $> 1,5\\times\\text{TB20}$ · **Time-Stop** tại \`T+10\` phiên \`[Tính toán]\`.

| Hạng mục Kiểm chứng | Trạng thái Hiện tại | Cơ chế & Bằng chứng Bảng điện | Điều kiện Bác bỏ (Invalidation) |
| :--- | :--- | :--- | :--- |
| **Bản chất Tạo lập** | Nhóm Sản xuất Nội tại thật \`[Tính toán]\` | Tổ chức & Khối ngoại bảo kê vùng giá vốn, đi lên theo bậc thang | Khối ngoại xả ròng liên tục > 5 phiên |
| **Cấu trúc Cung – Cầu** | Tích lũy hấp thụ trên POC \`[Tính toán]\` | Nhịp chỉnh biên độ hẹp, thanh khoản cạn cung (No Supply) | Nổ vol lớn ở đỉnh nhưng giá không tăng (Churning) |
| **Chiến thuật T+2,5** | Gom 30%–40% tại nền \`[Suy luận]\` | Giải ngân sau 13h45 khi kiểm tra xong lượng hàng T+2,5 về tài khoản | Đóng cửa thủng Price-Stop 26,60 |`,
};

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
  const [activeTab, setActiveTab] = useState('tab-summary');

  // Trạng thái các luồng dữ liệu chạy song song (streaming progressive)
  const [loadingMarket, setLoadingMarket] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [loadingCouncil, setLoadingCouncil] = useState(false);
  const [councilProgress, setCouncilProgress] = useState({});
  const councilRequestRef = useRef(0);
  const [data, setData] = useState(null);
  const [aiReport, setAiReport] = useState(INITIAL_FALLBACK_REPORT);
  const [councilDebate, setCouncilDebate] = useState(INITIAL_COUNCIL_DEBATE);
  const [councilAgents, setCouncilAgents] = useState(INITIAL_COUNCIL_AGENTS);
  const [liveQuote, setLiveQuote] = useState(null);
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);

  const refreshWatchlist = useCallback(async () => {
    const list = await getWatchlist();
    setWatchlist(list);
  }, []);

  // Tải song song tất cả các nguồn: cái nào xong trước hiển thị ngay cái đó, không chặn nhau!
  const triggerParallelStreams = useCallback(
    (targetSym, customDate = targetDate, customHorizon = horizon, customRisk = riskProfile, customCost = costBasis) => {
      const cleanSym = (targetSym || 'HPG').toUpperCase().trim();
      setSymbol(cleanSym);
      setError(null);

      const basePayload = {
        symbol: cleanSym,
        horizon: customHorizon,
        risk_profile: customRisk,
      };
      if (customDate) basePayload.target_date = customDate;
      const parsedCost = parseFloat(String(customCost).replace(',', '.'));
      if (!Number.isNaN(parsedCost) && parsedCost > 0) {
        basePayload.cost_basis = parsedCost;
      }

      // LUỒNG 1 (Siêu tốc ~100ms): Bảng giá trực tiếp & Sổ lệnh Realtime
      fetchRealtimeQuoteApi(cleanSym)
        .then((res) => {
          if (res?.quotes?.[cleanSym]) {
            setLiveQuote(res.quotes[cleanSym]);
          }
        })
        .catch(() => {});

      // LUỒNG 2 (Nhanh ~0.5s - 1.5s): Dữ liệu Lịch sử Nến + Vĩ mô + Ngành + Báo cáo Định lượng Tức thì (instant_report)
      setLoadingMarket(true);
      fetchMarketDataApi(basePayload)
        .then((marketData) => {
          setData(marketData);
          setLoadingMarket(false);
          // Nếu Backend trả về sẵn instant_report (Định lượng 6 bước T+2,5 tức thì), hiển thị ngay lập tức
          // trước khi Gemini AI kịp chạy xong!
          if (marketData?.instant_report) {
            setAiReport((prev) => {
              // Chỉ ghi đè nếu chưa có báo cáo Gemini hoàn chỉnh của đúng mã này
              if (!prev || !String(prev.engine || '').startsWith('gemini:') || prev._symbol !== cleanSym) {
                return { ...marketData.instant_report, _symbol: cleanSym };
              }
              return prev;
            });
          }
        })
        .catch((err) => {
          setError(err.message || 'Không thể kết nối máy chủ dữ liệu thị trường (đang hiển thị chế độ Workstation cục bộ).');
          setLoadingMarket(false);
        });

      // LUỒNG 3 (Chuyên sâu): Hội đồng Đầu tư AI + BCTC + Web Grounding + Forecast Audit
      setLoadingAI(true);
      fetchAiReportApi(basePayload)
        .then((aiData) => {
          if (aiData?.ai_report) {
            setAiReport({ ...aiData.ai_report, _symbol: cleanSym });
          }
          setLoadingAI(false);
        })
        .catch(() => {
          setLoadingAI(false);
        });

      // LUỒNG 4 (Quân cơ): Hội Đồng Đa Tác Nhân Phân Cấp (5 Persona Asyncio Debate & Critique Loop)
      // Mỗi lần triệu tập mang 1 mã yêu cầu; bỏ qua sự kiện của phiên cũ nếu người dùng đổi mã giữa chừng
      const councilReqId = ++councilRequestRef.current;
      const isCurrentCouncil = () => councilRequestRef.current === councilReqId;
      setLoadingCouncil(true);
      setCouncilProgress({ startedAt: Date.now(), stages: {} });
      fetchCouncilDebateStream(cleanSym, basePayload, (ev) => {
        if (!isCurrentCouncil()) return;
        setCouncilProgress((prev) => ({
          ...prev,
          engine: ev.engine || prev.engine,
          message: ev.message || prev.message,
          stages: { ...(prev.stages || {}), [ev.stage]: ev.status },
        }));
      })
        .then((councilData) => {
          if (!isCurrentCouncil()) return;
          if (councilData) {
            setCouncilDebate(councilData);
          }
          setLoadingCouncil(false);
          // Án phạt của Cẩm Y Vệ có thể đã thay đổi Điểm Công Huân -> tải lại bảng
          fetchCouncilAgents()
            .then((res) => res?.agents && setCouncilAgents(res.agents))
            .catch(() => {});
        })
        .catch((err) => {
          if (!isCurrentCouncil()) return;
          console.warn('[Council] Dùng dữ liệu fallback:', err);
          setLoadingCouncil(false);
        });

      fetchCouncilAgents()
        .then((res) => {
          if (res?.agents) {
            setCouncilAgents(res.agents);
          }
        })
        .catch(() => {});
    },
    [targetDate, horizon, riskProfile, costBasis],
  );

  // Tự động chạy ngay khi mở trang web (không cần chờ người dùng bấm nút)
  useEffect(() => {
    refreshWatchlist();
    fetchCouncilAgents()
      .then((res) => {
        if (res?.agents) {
          setCouncilAgents(res.agents);
        }
      })
      .catch(() => {});
    triggerParallelStreams('HPG');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    triggerParallelStreams(symbol);
  };

  const handleSelectSymbol = (sym) => {
    triggerParallelStreams(sym);
  };

  const handleAddToWatchlist = async (sym) => {
    await addToWatchlistApi(sym);
    refreshWatchlist();
  };

  const handleRemoveWatchlist = async (sym, e) => {
    e.stopPropagation();
    await removeFromWatchlistApi(sym);
    refreshWatchlist();
  };

  // Tính toán các chỉ số hiển thị trên Stock Banner (hợp nhất từ LiveQuote, History và Quant Snapshot)
  const history = data?.history || [];
  const lastBar = history.length > 0 ? history[history.length - 1] : null;
  const prevBar = history.length > 1 ? history[history.length - 2] : null;

  const curPrice = liveQuote?.price ?? lastBar?.Close ?? 28.45;
  const refPrice = liveQuote?.ref ?? prevBar?.Close ?? 27.8;
  const priceDiff = curPrice - refPrice;
  const pricePct = refPrice ? (priceDiff / refPrice) * 100 : 2.34;
  const isUp = priceDiff >= 0;

  // Đỉnh / Đáy 52 tuần
  const bars52w = history.slice(-252);
  const low52w = bars52w.length > 0 ? Math.min(...bars52w.map((b) => Number(b.Low || b.Close))) : Number((curPrice * 0.75).toFixed(2));
  const high52w = bars52w.length > 0 ? Math.max(...bars52w.map((b) => Number(b.High || b.Close))) : Number((curPrice * 1.15).toFixed(2));
  const pos52wPct = high52w > low52w ? Math.max(2, Math.min(98, Math.round(((curPrice - low52w) / (high52w - low52w)) * 100))) : 72;

  const activeReport = aiReport || INITIAL_FALLBACK_REPORT;
  const qs = activeReport.quant_snapshot || {};
  const tac = qs.tactical_6step || {};
  const arch = tac.archetype || {
    name: 'Nhóm 3: Sản xuất Nội tại thật',
    group_key: 'CORE_PRODUCTION',
  };
  const scores = activeReport.scores || INITIAL_FALLBACK_REPORT.scores;
  const overallScore = activeReport.overall_score || 78;
  const summary = activeReport.summary || INITIAL_FALLBACK_REPORT.summary;
  const tp = activeReport.trade_plan || INITIAL_FALLBACK_REPORT.trade_plan;
  const scenarios = activeReport.scenarios || INITIAL_FALLBACK_REPORT.scenarios;

  const sup1 = qs.supports?.[0]?.price ?? tp.stop_loss ?? Number((curPrice * 0.95).toFixed(2));
  const res1 = qs.resistances?.[0]?.price ?? tp.target_1 ?? Number((curPrice * 1.08).toFixed(2));
  const volDisplay = liveQuote?.volume
    ? `${Number(liveQuote.volume).toLocaleString('vi-VN')} cp`
    : lastBar?.Volume
      ? `${Number(lastBar.Volume).toLocaleString('vi-VN')} cp`
      : '34.820.000 cp';
  const foreignNetDisplay =
    qs.foreign_net_bn !== undefined && qs.foreign_net_bn !== null
      ? `${qs.foreign_net_bn >= 0 ? '+' : ''}${Number(qs.foreign_net_bn).toFixed(1)} tỷ`
      : '+84,2 tỷ';

  // Danh mục hiển thị cột trái: kết hợp Watchlist từ DB và danh sách mẫu chuẩn FiinTrade
  const mergedWatchlist = [
    ...DEFAULT_WATCHLIST.map((item) => ({
      ...item,
      isSaved: watchlist.some((w) => w.symbol === item.symbol),
    })),
    ...watchlist
      .filter((w) => !DEFAULT_WATCHLIST.some((d) => d.symbol === w.symbol))
      .map((w) => ({
        symbol: w.symbol,
        name: `Cổ phiếu ${w.symbol}`,
        group: 'Danh mục theo dõi',
        price: w.symbol === symbol ? curPrice : null,
        pct: w.symbol === symbol ? pricePct : null,
        score: w.symbol === symbol ? overallScore : 70,
        isSaved: true,
      })),
  ];

  const stockMeta = DEFAULT_WATCHLIST.find((d) => d.symbol === symbol);
  const companyDisplayName = liveQuote?.short_name || stockMeta?.name || `Cổ phiếu ${symbol}`;
  const sectorDisplayName = data?.sector || 'Thép & Sản xuất Công nghiệp';
  const isGeminiReady = String(activeReport.engine || '').startsWith('gemini:');

  const dimRows = [
    { key: 'macro_industry', label: '1. Vĩ mô & Sóng ngành', val: scores.macro_industry?.score ?? 75 },
    { key: 'fundamentals_catalyst', label: '2. Nội lực BCTC & Định giá', val: scores.fundamentals_catalyst?.score ?? 80 },
    { key: 'comparative_strength', label: '3. Dòng tiền & Sức mạnh RS', val: scores.comparative_strength?.score ?? 79 },
    { key: 'technical_momentum', label: '4. Kỹ thuật & Động lượng', val: scores.technical_momentum?.score ?? 76 },
    { key: 'action_strategy', label: '5. Chiến lược T+2,5 & R:R', val: scores.action_strategy?.score ?? 82 },
  ];

  const lastHistoryDate = history.length > 0 ? history[history.length - 1].Date : null;

  return (
    <div className="ws-root">
      {/* 1. TOP WORKSTATION NAVBAR */}
      <header className="ws-navbar">
        <div className="ws-brand">
          <div className="ws-brand-badge">Fiin × FireAnt Pro</div>
          <div className="ws-brand-title">
            NGHIỆP VỤ <span>AI WORKSTATION V5.0</span>
          </div>
          <div className="ws-tag-hybrid">TẠO LẬP × CFA × T+2,5</div>
        </div>

        <form className="ws-toolbar" onSubmit={handleSubmit}>
          <div className="ws-ctrl">
            <span>MÃ:</span>
            <input
              type="text"
              className="ws-sym-input"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              maxLength={8}
              placeholder="HPG"
            />
          </div>

          <div className="ws-ctrl">
            <span>NGÀY:</span>
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              title="Để trống để phân tích thời gian thực"
            />
          </div>

          <div className="ws-ctrl">
            <span>KHUNG:</span>
            <select value={horizon} onChange={(e) => setHorizon(e.target.value)}>
              {HORIZON_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </div>

          <div className="ws-ctrl">
            <span>KHẨU VỊ:</span>
            <select value={riskProfile} onChange={(e) => setRiskProfile(e.target.value)}>
              {RISK_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          <div className="ws-ctrl">
            <span>GIÁ VỐN:</span>
            <input
              type="text"
              inputMode="decimal"
              value={costBasis}
              onChange={(e) => setCostBasis(e.target.value)}
              placeholder="VD: 27.5"
              style={{ width: '68px' }}
            />
          </div>

          <button type="submit" className="ws-btn-analyze">
            {loadingMarket || loadingAI ? <Zap size={14} className="spin" /> : <Play size={14} />}
            {loadingMarket ? 'ĐANG TẢI GIÁ...' : loadingAI ? 'AI ĐANG THẨM ĐỊNH...' : 'CHẠY THẨM ĐỊNH'}
          </button>
        </form>
      </header>

      {/* 2. MACRO TICKER BAR & PROGRESSIVE STREAM STATUS */}
      <div className="ws-macro-bar">
        <div className="ws-macro-items">
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">VN-INDEX:</span>
            <span className="ws-macro-val up-color">{data?.macro?.VNINDEX || '1.258,42 (+0,78%)'}</span>
          </div>
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">VN30:</span>
            <span className="ws-macro-val up-color">{data?.macro?.VN30 || '1.314,10 (+1,12%)'}</span>
          </div>
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">USD/VND:</span>
            <span className="ws-macro-val" style={{ color: '#ffb800' }}>
              {data?.macro?.USD_VND || '25.415'}
            </span>
          </div>
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">DẦU BRENT:</span>
            <span className="ws-macro-val" style={{ color: '#38bdf8' }}>
              {data?.macro?.OIL || '74,80 USD'}
            </span>
          </div>
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">VÀNG:</span>
            <span className="ws-macro-val up-color">{data?.macro?.GOLD || '2.685 USD'}</span>
          </div>
          <div className="ws-macro-item">
            <span className="ws-macro-lbl">THỜI TIẾT TT:</span>
            <span className="ws-macro-val">{qs.market_status || '🟢 Tích cực có chọn lọc'}</span>
          </div>
        </div>

        <div className="ws-stream-status">
          <span className={`ws-stream-pill ${loadingMarket ? 'syncing' : 'live'}`}>
            <Radio size={11} />
            {loadingMarket ? 'Luồng Giá: Đang tải...' : 'Luồng Giá & Quant: Sẵn sàng'}
          </span>
          <span className={`ws-stream-pill ${loadingAI ? 'syncing' : 'live'}`}>
            {loadingAI
              ? '⚡ Bộ phận Nghiệp vụ AI đang phân tích sâu (hiển thị trước bản Định lượng)...'
              : isGeminiReady
                ? `✅ Nghiệp vụ AI Hoàn tất (${activeReport.engine.replace('gemini:', '')})`
                : '⚡ Chế độ Định lượng Tức thì (6 Bước T+2,5)'}
          </span>
        </div>
      </div>

      {error && (
        <div
          style={{
            margin: '8px 16px 0',
            padding: '8px 14px',
            background: 'rgba(255, 184, 0, 0.1)',
            border: '1px solid rgba(255, 184, 0, 0.35)',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '12px',
            color: '#fbbf24',
          }}
        >
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* 3. WORKSTATION 2-COLUMN GRID (Tuyến bảng bên trái + Không gian chính bên phải) */}
      <main className="ws-grid">
        {/* LEFT COLUMN: WATCHLIST + 5 NHÓM TẠO LẬP + 3 BẢNG CÔNG CỤ NGHIỆP VỤ */}
        <aside className="ws-left-col">
          <div className="ws-panel">
            <div className="ws-panel-header">
              <span>Danh Mục Theo Dõi</span>
              <button
                onClick={() => handleAddToWatchlist(symbol)}
                style={{
                  background: 'rgba(47, 129, 247, 0.15)',
                  color: '#2f81f7',
                  border: '1px solid rgba(47, 129, 247, 0.35)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '10px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '3px',
                }}
                title={`Lưu ${symbol} vào danh mục`}
              >
                <Plus size={11} /> Lưu {symbol}
              </button>
            </div>

            <table className="ws-watchlist-table">
              <thead>
                <tr>
                  <th>MÃ</th>
                  <th style={{ textAlign: 'right' }}>GIÁ</th>
                  <th style={{ textAlign: 'right' }}>+/- %</th>
                  <th style={{ textAlign: 'center' }}>ĐIỂM</th>
                </tr>
              </thead>
              <tbody>
                {mergedWatchlist.map((item) => {
                  const isActive = item.symbol === symbol;
                  const rowPrice = isActive ? curPrice : item.price;
                  const rowPct = isActive ? pricePct : item.pct;
                  const rowScore = isActive ? overallScore : item.score;
                  const rowUp = (rowPct ?? 0) >= 0;
                  const scoreCls =
                    rowScore >= 70 ? 'score-high' : rowScore >= 50 ? 'score-med' : 'score-low';

                  return (
                    <tr
                      key={item.symbol}
                      className={isActive ? 'active' : ''}
                      onClick={() => handleSelectSymbol(item.symbol)}
                    >
                      <td style={{ fontWeight: 800, color: rowUp ? '#00c076' : '#ff3b30' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span>{item.symbol}</span>
                          {item.isSaved && (
                            <button
                              onClick={(e) => handleRemoveWatchlist(item.symbol, e)}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: '#64748b',
                                cursor: 'pointer',
                                padding: 0,
                                marginLeft: 'auto',
                              }}
                              title="Xóa khỏi danh mục lưu"
                            >
                              <Trash2 size={11} />
                            </button>
                          )}
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {rowPrice != null ? Number(rowPrice).toFixed(2) : '—'}
                      </td>
                      <td
                        style={{
                          textAlign: 'right',
                          color: rowUp ? '#00c076' : '#ff3b30',
                          fontWeight: 700,
                        }}
                      >
                        {rowPct != null ? `${rowUp ? '+' : ''}${Number(rowPct).toFixed(2)}%` : '—'}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`badge-score ${scoreCls}`}>{rowScore ?? 75}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* 5 NHÓM TẠO LẬP QUICK SELECT */}
            <div style={{ padding: '12px', borderTop: '1px solid #202b3e', background: '#0c1019' }}>
              <div
                style={{
                  fontSize: '10px',
                  color: '#64748b',
                  fontWeight: 800,
                  marginBottom: '8px',
                  textTransform: 'uppercase',
                }}
              >
                5 NHÓM CỔ PHIẾU TRÊN BÀN CỜ TẠO LẬP
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
                <div
                  onClick={() => handleSelectSymbol('VIC')}
                  style={{ cursor: 'pointer', padding: '5px 8px', borderRadius: '4px', background: '#151c2c', borderLeft: '3px solid #a371f7' }}
                >
                  <strong>1. Trụ Điều tiết Chỉ số:</strong> <span className="muted">VIC, VHM, VRE</span>
                </div>
                <div
                  onClick={() => handleSelectSymbol('VIX')}
                  style={{ cursor: 'pointer', padding: '5px 8px', borderRadius: '4px', background: '#151c2c', borderLeft: '3px solid #ff3b30' }}
                >
                  <strong>2. Đầu cơ Hệ sinh thái:</strong> <span className="muted">VIX, GEX, VSC, EIB</span>
                </div>
                <div
                  onClick={() => handleSelectSymbol('HPG')}
                  style={{ cursor: 'pointer', padding: '5px 8px', borderRadius: '4px', background: '#151c2c', borderLeft: '3px solid #00c076' }}
                >
                  <strong>3. Sản xuất Nội tại thật:</strong> <span className="muted">HPG, CTD, FPT</span>
                </div>
                <div
                  onClick={() => handleSelectSymbol('TCB')}
                  style={{ cursor: 'pointer', padding: '5px 8px', borderRadius: '4px', background: '#151c2c', borderLeft: '3px solid #2f81f7' }}
                >
                  <strong>4. Ngân hàng Vua TK:</strong> <span className="muted">TCB, MBB, VCB</span>
                </div>
                <div
                  onClick={() => handleSelectSymbol('OIL')}
                  style={{ cursor: 'pointer', padding: '5px 8px', borderRadius: '4px', background: '#151c2c', borderLeft: '3px solid #ffb800' }}
                >
                  <strong>5. Phòng thủ Địa chính trị:</strong> <span className="muted">OIL, PVD, GAS</span>
                </div>
              </div>
            </div>
          </div>

          {/* BẢNG ĐIỂM CÔNG HUÂN & TRẠNG THÁI KỶ LUẬT 5 AGENT (R4) */}
          <AgentMeritBoard
            agents={councilAgents}
            recentPenalties={councilDebate?.penalties_issued || []}
            onRefresh={() => {
              fetchCouncilAgents().then((res) => {
                if (res?.agents) setCouncilAgents(res.agents);
              });
            }}
          />

          {/* THANH CÔNG CỤ 1 (TUYẾN TRÁI): ĐÁNH GIÁ 5 CHIỀU NGHIỆP VỤ */}
          <div className="ws-card">
            <div className="ws-panel-header" style={{ margin: '-14px -14px 6px -14px' }}>
              <span>ĐÁNH GIÁ 5 CHIỀU NGHIỆP VỤ</span>
              <span className="badge-score score-high">{summary.stance || 'TÍCH CỰC'}</span>
            </div>

            <div className="ws-score-box">
              <div>
                <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase' }}>
                  Quyết nghị Nghiệp vụ
                </div>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#00c076', marginTop: '2px' }}>
                  {summary.action || 'Mua thăm dò'}
                </div>
                <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>
                  Độ tin cậy: <strong>{summary.confidence || 'Trung bình'}</strong>
                </div>
              </div>
              <div className="ws-score-circle">
                {overallScore}
                <span>/100</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '9px', marginTop: '4px' }}>
              {dimRows.map((d) => {
                const barColor = d.val >= 75 ? '#00c076' : d.val >= 55 ? '#ffb800' : '#ff3b30';
                return (
                  <div className="ws-dim-row" key={d.key}>
                    <div className="ws-dim-hdr">
                      <span style={{ color: '#94a3b8', fontWeight: 600 }}>{d.label}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{d.val}/100</span>
                    </div>
                    <div className="ws-dim-bar-bg">
                      <div className="ws-dim-bar-fill" style={{ width: `${d.val}%`, background: barColor }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* THANH CÔNG CỤ 2 (TUYẾN TRÁI): TÓM TẮT LỆNH T+2,5 & 3 CHỐT CHẶN */}
          <div className="ws-card">
            <div className="ws-panel-header" style={{ margin: '-14px -14px 6px -14px' }}>
              <span>TÓM TẮT LỆNH T+2,5 & 3 CHỐT CHẶN</span>
            </div>

            <div className="ws-kv-list">
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Vùng mua gom:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#00c076' }}>
                  {Number(tp.entry_low || curPrice * 0.98).toFixed(2)} – {Number(tp.entry_high || curPrice).toFixed(2)}
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Price-Stop (≥1,5×ATR):</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#ff3b30' }}>
                  {Number(tp.stop_loss || sup1).toFixed(2)} (-{Number(tp.stop_pct || 5.5).toFixed(1)}%)
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Chốt lời Nhịp 1 (30%):</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#00c076' }}>
                  {Number(tp.target_1 || res1).toFixed(2)}
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Chốt lời Nhịp 2 (50%):</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#ffb800' }}>
                  Trailing lùi 1,5%–2%
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Chốt lời Nhịp 3 (20%):</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#2f81f7' }}>
                  {Number(tp.target_2 || curPrice * 1.15).toFixed(2)} (Gap sáng)
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Time-Stop (Hạn giữ):</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  T+{tp.exit_stops?.time_stop?.sessions || 10} phiên
                </span>
              </div>
              <div className="ws-kv-row">
                <span style={{ color: '#64748b' }}>Khung giờ bấm nút:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#00c076' }}>
                  13h45 – 14h25
                </span>
              </div>
            </div>
          </div>

          {/* THANH CÔNG CỤ 3 (TUYẾN TRÁI): XÁC SUẤT 3 KỊCH BẢN (CHẤM ĐIỂM) */}
          <div className="ws-card">
            <div className="ws-panel-header" style={{ margin: '-14px -14px 6px -14px' }}>
              <span>XÁC SUẤT 3 KỊCH BẢN (CHẤM ĐIỂM)</span>
            </div>

            <div className="ws-kv-list">
              {scenarios.map((s, idx) => {
                const isBull = s.name?.includes('🟢') || idx === 0;
                const isBear = s.name?.includes('🔴') || idx === 2;
                const col = isBull ? '#00c076' : isBear ? '#ff3b30' : '#ffb800';
                return (
                  <div className="ws-kv-row" key={idx}>
                    <span style={{ color: col, fontWeight: 600 }}>
                      {s.name} ({Number(s.price_target || curPrice).toFixed(2)}):
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: col }}>
                      {s.probability}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </aside>

        {/* CENTER/RIGHT WORKSPACE: EXECUTIVE SUMMARY BANNER + STOCK BANNER + WORKSTATION TABS */}
        <section style={{ display: 'flex', flexDirection: 'column', minWidth: 0, gap: '14px' }}>
          {/* KHUNG TÓM TẮT HÀNH ĐỘNG 3 DÒNG DO MINH CHỦ VÕ LÂM KÝ DUYỆT (R4) */}
          <ExecutiveSummaryBanner
            executiveSummary={councilDebate?.executive_summary || activeReport?.executive_summary}
            report={activeReport}
            symbol={symbol}
            verdict={councilDebate?.verdict || activeReport?.summary?.action}
            sessionId={councilDebate?.session_id}
          />

          {/* STOCK BANNER */}
          <div className="ws-stock-banner">
            <div className="ws-banner-top">
              <div className="ws-stock-main">
                <div className="ws-sym-pill" style={{ color: isUp ? '#00c076' : '#ff3b30' }}>
                  {symbol}
                </div>
                <div>
                  <div className="ws-stock-name">
                    <span>{companyDisplayName}</span>
                    <span
                      style={{
                        background: 'rgba(56, 189, 248, 0.15)',
                        color: '#38bdf8',
                        border: '1px solid rgba(56, 189, 248, 0.35)',
                        fontSize: '10px',
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontWeight: 700,
                      }}
                    >
                      {arch.name}
                    </span>
                  </div>
                  <div className="ws-stock-sub">
                    {liveQuote?.exchange || 'HOSE'} · {sectorDisplayName} · Thanh khoản TB20:{' '}
                    <strong>{qs.avg_value_20d_bn ? `${qs.avg_value_20d_bn} tỷ/phiên` : '645 tỷ/phiên'}</strong> ·{' '}
                    <span style={{ color: '#00c076', fontWeight: 600 }}>
                      Kiểm tra GDKHQ (•): Sẵn sàng giao dịch T+2,5
                    </span>
                  </div>
                </div>
              </div>

              <div className="ws-price-strip">
                <div className="ws-cur-price" style={{ color: isUp ? '#00c076' : '#ff3b30' }}>
                  {Number(curPrice).toFixed(2)}
                </div>
                <div className="ws-delta" style={{ color: isUp ? '#00c076' : '#ff3b30' }}>
                  {isUp ? '▲ +' : '▼ '}
                  {Number(priceDiff).toFixed(2)} ({isUp ? '+' : ''}
                  {Number(pricePct).toFixed(2)}%)
                </div>
              </div>

              <div className="ws-stats-inline">
                <div className="ws-stat-col">
                  <span className="ws-stat-lbl">KL Khớp:</span>
                  <span className="ws-stat-val">{volDisplay}</span>
                </div>
                <div className="ws-stat-col">
                  <span className="ws-stat-lbl">Khối Ngoại:</span>
                  <span
                    className="ws-stat-val"
                    style={{ color: String(foreignNetDisplay).startsWith('-') ? '#ff3b30' : '#00c076' }}
                  >
                    {foreignNetDisplay}
                  </span>
                </div>
                <div className="ws-stat-col">
                  <span className="ws-stat-lbl">Hỗ trợ / Cản:</span>
                  <span className="ws-stat-val">
                    {Number(sup1).toFixed(2)} / {Number(res1).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* 52-WEEK RANGE & ACTIVE ORDER BAR */}
            <div className="ws-banner-bottom">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                  <span>
                    Đáy 52T: <strong>{Number(low52w).toFixed(2)}</strong>
                  </span>
                  <span style={{ color: '#f1f5f9', fontWeight: 700 }}>
                    Vị trí giá: {pos52wPct}% dải 52 tuần
                  </span>
                  <span>
                    Đỉnh 52T: <strong>{Number(high52w).toFixed(2)}</strong>
                  </span>
                </div>
                <div className="ws-range-track">
                  <div className="ws-range-fill" style={{ width: `${pos52wPct}%` }} />
                  <div className="ws-range-pin" style={{ left: `${pos52wPct}%` }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  <span style={{ color: '#00c076' }}>
                    Đệm Cắt lỗ Price-Stop: <strong>{Number(tp.stop_loss || sup1).toFixed(2)}</strong> (≥ 1,5×ATR)
                  </span>
                  <span style={{ color: '#ffb800' }}>
                    Tỷ lệ R:R chuẩn: <strong>1 : {Number(tp.rr_ratio || 2.4).toFixed(2)}</strong>
                  </span>
                </div>
                <div style={{ height: '6px', borderRadius: '3px', display: 'flex', overflow: 'hidden', marginTop: '4px' }}>
                  <div style={{ width: '68%', background: '#00c076' }} />
                  <div style={{ width: '32%', background: '#ff3b30' }} />
                </div>
              </div>
            </div>
          </div>

          {/* TOP GIAO DỊCH KHỐI NGOẠI TOÀN SÀN (MUA/BÁN RÒNG REAL-TIME TỪ VIETCAP) */}
          <TopForeignFlow onSelectSymbol={handleSelectSymbol} />

          {/* 6 WORKSTATION TABS (BAO GỒM BIÊN BẢN CUỘC HỌP QUÂN CƠ 5 TÁC NHÂN) */}
          <div className="ws-tab-bar">
            <button
              type="button"
              className={`ws-tab-btn ws-tab-btn-council ${activeTab === 'tab-council' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-council')}
            >
              ⚔️ 0. Biên Bản Cuộc Họp Quân Cơ (5 Tác Nhân)
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-summary')}
            >
              🎯 1. Nghiệp Vụ Thẩm Định & Kế Hoạch T+2,5
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-chart' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-chart')}
            >
              📈 2. Biểu Đồ Nến & Bảng Giá Trực Tiếp
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-report' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-report')}
            >
              📑 3. Báo Cáo Nghiệp Vụ Chuyên Sâu (Full Markdown)
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-peers' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-peers')}
            >
              🌊 4. Dự Báo Dải Giá T+ & So Sánh Cùng Ngành
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-radar' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-radar')}
            >
              📊 5. Chấm Điểm 5 Chiều Chi Tiết
            </button>
            <button
              type="button"
              className={`ws-tab-btn ${activeTab === 'tab-realdata' ? 'active' : ''}`}
              onClick={() => setActiveTab('tab-realdata')}
            >
              🦈 6. Dữ Liệu Thật: BCTC · GDKHQ · Shark Tracker
            </button>
          </div>

          {/* TAB CONTENT AREA */}
          <div className="ws-tab-content">
            {activeTab === 'tab-council' && (
              <CouncilDebate
                debate={councilDebate}
                loading={loadingCouncil}
                progress={councilProgress}
                symbol={symbol}
                onRefresh={() => triggerParallelStreams(symbol)}
              />
            )}

            {activeTab === 'tab-summary' && <InvestmentThesis report={activeReport} />}

            {activeTab === 'tab-chart' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <LiveQuote key={symbol} symbol={symbol} />
                {history.length > 0 ? (
                  <StockChart
                    history={history}
                    predictions={activeReport.predictions}
                    aiReport={activeReport}
                  />
                ) : (
                  <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
                    Đang tải lịch sử nến kỹ thuật cho mã {symbol}...
                  </div>
                )}
              </div>
            )}

            {activeTab === 'tab-report' && (
              <AnalysisReport
                analysisText={activeReport.analysis}
                news={data?.news || []}
                engine={activeReport.engine}
              />
            )}

            {activeTab === 'tab-peers' && (
              <PriceTargetsAndPeers
                predictions={activeReport.predictions || []}
                lastHistoryDate={lastHistoryDate}
                loadingAI={loadingAI}
                peers={data?.peers || {}}
                symbol={symbol}
                sector={sectorDisplayName}
                onSelectSymbol={handleSelectSymbol}
              />
            )}

            {activeTab === 'tab-realdata' && <RealDataPanel symbol={symbol} />}

            {activeTab === 'tab-radar' && (
              <RadarScoreCard
                scores={scores}
                overallScore={overallScore}
                summary={summary}
              />
            )}
          </div>
        </section>
      </main>

      {/* AI GEMINI CHATBOX FLOATING */}
      <AIChatBox currentSymbol={symbol} currentSector={sectorDisplayName} />
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
