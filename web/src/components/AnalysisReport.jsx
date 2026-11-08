import React, { useState, useEffect } from 'react';
import { FileText, Info, Newspaper } from 'lucide-react';

function renderInlineFormatting(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*.*?\*\*|\*[^*]+\*)/g);
  return parts.map((part, pi) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={pi} style={{ color: 'var(--text-active)' }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return (
        <em key={pi} style={{ color: 'var(--text-secondary)' }}>
          {part.slice(1, -1)}
        </em>
      );
    }
    return part;
  });
}

function renderTable(tableLines, keyPrefix) {
  const rows = tableLines.filter((row) => !/^\|\s*[-:]+/.test(row));
  if (rows.length === 0) return null;
  return (
    <div className="table-wrapper" key={`table-${keyPrefix}`}>
      <table className="analysis-table">
        <tbody>
          {rows.map((row, ri) => {
            const cols = row
              .replace(/^\|/, '')
              .replace(/\|$/, '')
              .split('|');
            return (
              <tr key={ri}>
                {cols.map((col, ci) => (
                  <td
                    key={ci}
                    style={{
                      fontWeight: ri === 0 ? '700' : '400',
                      background: ri === 0 ? 'rgba(47, 129, 247, 0.1)' : 'transparent',
                    }}
                  >
                    {renderInlineFormatting(col.trim())}
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

function formatMarkdownReport(text) {
  if (!text || typeof text !== 'string') return null;
  const lines = text.split('\n');
  const result = [];
  let tableLines = [];
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith('|')) {
      inTable = true;
      tableLines.push(line);
      continue;
    } else if (inTable) {
      const tbl = renderTable(tableLines, i);
      if (tbl) result.push(tbl);
      tableLines = [];
      inTable = false;
    }

    if (line === '' || line === '---') continue;

    if (line.startsWith('###')) {
      result.push(<h3 key={i}>{line.replace(/^#+\s*/, '')}</h3>);
    } else if (line.startsWith('##')) {
      result.push(
        <h2 key={i} className="report-h2">
          {line.replace(/^#+\s*/, '')}
        </h2>
      );
    } else if (line.startsWith('#')) {
      result.push(
        <h2 key={i} className="report-h2">
          {line.replace(/^#+\s*/, '')}
        </h2>
      );
    } else if (line.startsWith('>')) {
      result.push(
        <blockquote key={i} className="report-blockquote">
          {renderInlineFormatting(line.replace(/^>\s*/, ''))}
        </blockquote>
      );
    } else {
      const isListItem = line.startsWith('- ') || line.startsWith('+ ') || line.startsWith('* ');
      const cleanLine = isListItem ? '• ' + line.slice(2) : line;
      result.push(
        <p
          key={i}
          style={{
            textAlign: 'left',
            marginLeft: isListItem ? '1.2rem' : '0',
            textIndent: isListItem ? '-0.8rem' : '0',
          }}
        >
          {renderInlineFormatting(cleanLine)}
        </p>
      );
    }
  }

  // Flush bảng nếu nằm ở cuối báo cáo
  if (inTable && tableLines.length > 0) {
    const tbl = renderTable(tableLines, 'end');
    if (tbl) result.push(tbl);
  }

  return result;
}

export default function AnalysisReport({ analysisText, news, engine }) {
  const [displayedText, setDisplayedText] = useState('');
  const [prevAnalysis, setPrevAnalysis] = useState(analysisText);

  // Chuẩn React 19: Điều chỉnh state trong quá trình render khi prop thay đổi
  if (analysisText !== prevAnalysis) {
    setPrevAnalysis(analysisText);
    setDisplayedText('');
  }

  useEffect(() => {
    if (!analysisText) return;

    // Gõ nhanh theo cụm 45 ký tự mỗi 18ms để mượt mà và không làm giật React khi render bảng
    let idx = 0;
    const step = 45;
    const timer = setInterval(() => {
      idx += step;
      if (idx >= analysisText.length) {
        setDisplayedText(analysisText);
        clearInterval(timer);
      } else {
        setDisplayedText(analysisText.slice(0, idx));
      }
    }, 18);

    return () => clearInterval(timer);
  }, [analysisText]);

  if (!analysisText) return null;

  const isStreaming = displayedText.length < analysisText.length;

  return (
    <div className="bottom-cards-row" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="glass-panel analysis-card">
        <div className="section-title">
          <FileText size={18} color="var(--accent-blue)" />
          <h2>Báo Cáo Phân Tích Chuyên Sâu — Hội Đồng Đầu Tư AI</h2>
        </div>

        {(engine === 'rule_based' || (!engine && analysisText.includes('Chế độ Phân tích Định lượng Tự động'))) && (
          <div className="warning-box">
            <Info size={16} />
            <span>
              Đang hiển thị bản phân tích định lượng tự động (tính từ dữ liệu giao dịch thật, chưa đánh giá BCTC) vì chưa gọi
              được Gemini — thường do hết quota theo phút/ngày hoặc thiếu <code>GEMINI_API_KEY</code>. Thử phân tích lại sau ít phút.
            </span>
          </div>
        )}

        <div className="analysis-content">
          {formatMarkdownReport(displayedText)}
          {isStreaming && <span className="typewriter-cursor"></span>}
        </div>
      </div>

      {Array.isArray(news) && news.length > 0 && (
        <div className="glass-panel analysis-card">
          <div className="section-title">
            <Newspaper size={18} color="var(--accent-gold)" />
            <h2>Điểm Tin Tài Chính & Sự Kiện Liên Quan</h2>
          </div>
          <ul className="news-list">
            {news.map((item, idx) => (
              <li key={idx}>{item.replace(/^-\s*/, '')}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

