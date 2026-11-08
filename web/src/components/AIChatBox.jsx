import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  X,
  Send,
  Globe,
  ExternalLink,
  Bot,
  User,
  Trash2,
  Minimize2,
  Maximize2,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';
import { sendChatQueryApi } from '../services/apiClient';

export default function AIChatBox({ currentSymbol, currentSector }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Xin chào! Tôi là **AI Trợ lý Thị trường (Gemini Live Search)**. Tôi có thể tra cứu thông tin thời gian thực trên Internet, cập nhật tin tức báo chí, chỉ số vĩ mô và phân tích kỹ thuật theo mã cổ phiếu bạn đang xem.`,
      sources: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, messages]);

  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    const userMsg = {
      id: Date.now() + '_user',
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      // Chuẩn bị lịch sử hội thoại gần nhất
      const historyPayload = messages
        .filter((m) => m.id !== 'welcome')
        .slice(-6)
        .map((m) => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          content: m.content,
        }));

      const res = await sendChatQueryApi(query, historyPayload, currentSymbol);

      const aiMsg = {
        id: Date.now() + '_ai',
        role: 'assistant',
        content: res.reply || 'Không nhận được câu trả lời từ máy chủ.',
        sources: res.sources || [],
        engine: res.engine || 'Gemini Live Grounding',
        grounded: res.grounded,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now() + '_err',
        role: 'assistant',
        content: `⚠️ **Lỗi kết nối:** ${err.message || 'Không thể tra cứu thông tin vào lúc này. Vui lòng thử lại sau.'}`,
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome_reset',
        role: 'assistant',
        content: `Đã làm mới phiên hội thoại. Bạn muốn tra cứu thông tin gì về cổ phiếu **${currentSymbol || 'thị trường'}**?`,
        sources: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Render markdown đơn giản (headings, bold, lists, links)
  const renderFormattedContent = (content) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      let formattedLine = line;

      // Tiêu đề ###
      if (formattedLine.startsWith('### ')) {
        return (
          <h4 key={idx} className="chat-h4">
            {formattedLine.replace('### ', '')}
          </h4>
        );
      }
      if (formattedLine.startsWith('#### ')) {
        return (
          <h5 key={idx} className="chat-h5">
            {formattedLine.replace('#### ', '')}
          </h5>
        );
      }

      // Gạch đầu dòng
      const isBullet = formattedLine.trim().startsWith('- ') || formattedLine.trim().startsWith('* ');
      if (isBullet) {
        const bulletText = formattedLine.trim().replace(/^[-*]\s+/, '');
        return (
          <div key={idx} className="chat-bullet">
            <span className="bullet-dot">•</span>
            <span>{parseInlineFormatting(bulletText)}</span>
          </div>
        );
      }

      // Dòng trống
      if (!formattedLine.trim()) {
        return <div key={idx} className="chat-spacer" />;
      }

      return (
        <p key={idx} className="chat-p">
          {parseInlineFormatting(formattedLine)}
        </p>
      );
    });
  };

  const parseInlineFormatting = (text) => {
    // Chuyển bold **text** và [text](url)
    const parts = [];
    let keyIdx = 0;

    const regex = /(\*\*.*?\*\*|\[.*?\]\(.*?\))/g;
    let match;
    let lastIndex = 0;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(<strong key={keyIdx++}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith('[') && token.includes('](')) {
        const linkMatch = token.match(/\[(.*?)\]\((.*?)\)/);
        if (linkMatch) {
          parts.push(
            <a
              key={keyIdx++}
              href={linkMatch[2]}
              target="_blank"
              rel="noopener noreferrer"
              className="chat-link"
            >
              {linkMatch[1]} <ExternalLink size={11} style={{ display: 'inline', verticalAlign: 'middle' }} />
            </a>
          );
        }
      }
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  const suggestionChips = [
    `Tin tức mới nhất về ${currentSymbol || 'HPG'}?`,
    `Tác động vĩ mô (Tỷ giá & Giá Dầu)?`,
    `Kế hoạch chốt lời / cắt lỗ T+2.5?`,
    `So sánh ${currentSymbol || 'HPG'} với các mã cùng ngành`,
  ];

  return (
    <>
      {/* Floating Action Trigger Button */}
      {!isOpen && (
        <button
          className="ai-chat-trigger"
          onClick={() => setIsOpen(true)}
          title="Mở Trợ lý Tra cứu AI (Gemini Live Grounding)"
        >
          <div className="trigger-glow" />
          <div className="trigger-content">
            <Sparkles className="sparkle-icon" size={20} />
            <span className="trigger-title">AI Tra cứu Live</span>
            {currentSymbol && <span className="trigger-chip">{currentSymbol}</span>}
          </div>
        </button>
      )}

      {/* Floating Interactive Chat Panel */}
      {isOpen && (
        <div className={`ai-chat-window ${isExpanded ? 'chat-expanded' : ''}`}>
          {/* Header */}
          <div className="chat-header">
            <div className="header-info">
              <div className="ai-status-badge">
                <span className="pulse-dot"></span>
                <Globe size={14} className="globe-icon" />
              </div>
              <div>
                <div className="header-title-row">
                  <span className="header-name">Gemini Market Research</span>
                  <span className="grounding-badge">Live Web</span>
                </div>
                {currentSymbol && (
                  <div className="context-chip">
                    <TrendingUp size={11} />
                    <span>
                      Bối cảnh: <strong>{currentSymbol}</strong> {currentSector ? `• ${currentSector}` : ''}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="header-actions">
              <button
                className="icon-action-btn"
                onClick={clearChat}
                title="Làm mới đoạn hội thoại"
              >
                <Trash2 size={15} />
              </button>
              <button
                className="icon-action-btn"
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? 'Thu nhỏ' : 'Phóng to'}
              >
                {isExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
              </button>
              <button
                className="icon-action-btn close-btn"
                onClick={() => setIsOpen(false)}
                title="Đóng chatbox"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages Container */}
          <div className="chat-messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`chat-message-row ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                </div>
                <div className="message-bubble-wrapper">
                  <div className="message-bubble">
                    {renderFormattedContent(msg.content)}

                    {/* Hiển thị danh sách nguồn trích dẫn từ Internet */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="citations-block">
                        <div className="citations-label">
                          <Globe size={12} />
                          <span>Nguồn tra cứu thực tế trên Internet:</span>
                        </div>
                        <div className="citations-list">
                          {msg.sources.map((s, idx) => (
                            <a
                              key={idx}
                              href={s.url || '#'}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="citation-pill"
                              title={s.title}
                            >
                              <span className="source-index">[{idx + 1}]</span>
                              <span className="source-title">{s.title || s.source}</span>
                              <ExternalLink size={10} />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="message-meta">
                    <span className="msg-time">{msg.timestamp}</span>
                    {msg.engine && <span className="msg-engine">{msg.engine}</span>}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="chat-message-row assistant">
                <div className="message-avatar">
                  <Bot size={16} />
                </div>
                <div className="message-bubble-wrapper">
                  <div className="message-bubble typing-bubble">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span className="typing-text">Đang tra cứu dữ liệu thời gian thực trên mạng...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestion Chips */}
          <div className="chat-suggestions-bar">
            {suggestionChips.map((chip, idx) => (
              <button
                key={idx}
                className="suggestion-chip"
                onClick={() => handleSendMessage(chip)}
                disabled={loading}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Footer */}
          <div className="chat-input-footer">
            <div className="input-box-wrapper">
              <input
                ref={inputRef}
                type="text"
                className="chat-text-input"
                placeholder={
                  currentSymbol
                    ? `Tra cứu tin tức, vĩ mô, đối thủ của ${currentSymbol}...`
                    : 'Tra cứu tin tức thị trường, chỉ báo, vĩ mô...'
                }
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />
              <button
                className="chat-send-btn"
                onClick={() => handleSendMessage()}
                disabled={!inputMessage.trim() || loading}
                title="Gửi câu hỏi"
              >
                {loading ? <RefreshCw className="spin" size={16} /> : <Send size={16} />}
              </button>
            </div>
            <div className="footer-notice">
              <span>Được hỗ trợ bởi Google Gemini 2.5 với Google Live Search Grounding</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
