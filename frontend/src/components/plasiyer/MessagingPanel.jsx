import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Send, Loader2, MessageSquare } from 'lucide-react';
import { messagesAPI } from '../../services/api';

const MessagingPanel = ({ customer, onClose }) => {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const currentUser = (() => {
    try { return JSON.parse(localStorage.getItem('user')); } catch { return null; }
  })();

  const loadMessages = useCallback(async (convId) => {
    try {
      const res = await messagesAPI.listMessages(convId);
      setMessages(res.data || []);
      await messagesAPI.markRead(convId);
    } catch {
      // sessizce devam
    }
  }, []);

  useEffect(() => {
    if (!customer?.user_id) {
      setError('Müşteri kullanıcı bilgisi bulunamadı');
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await messagesAPI.createConversation({
          participant_ids: [customer.user_id],
        });
        if (cancelled) return;
        const convId = res.data.id;
        setConversationId(convId);
        await loadMessages(convId);
      } catch (err) {
        if (!cancelled) setError('Konuşma açılamadı');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [customer, loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || !conversationId || sending) return;
    setSending(true);
    setInputText('');
    try {
      const res = await messagesAPI.sendMessage(conversationId, text);
      setMessages(prev => [...prev, res.data]);
    } catch {
      setInputText(text);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-950/30 backdrop-blur-[2px] px-0 sm:px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="messaging-panel-overlay"
    >
      <div
        className="w-full sm:w-[420px] h-[90vh] sm:h-[600px] flex flex-col rounded-t-3xl sm:rounded-3xl bg-white shadow-2xl border border-slate-200 overflow-hidden"
        data-testid="messaging-panel"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100 flex-shrink-0">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
            <MessageSquare className="w-5 h-5 text-orange-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-slate-900 truncate" data-testid="messaging-panel-name">
              {customer?.name}
            </p>
            <p className="text-xs text-slate-400">Dahili mesajlaşma</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors text-slate-500"
            data-testid="messaging-panel-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3" data-testid="messaging-panel-messages">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-6 h-6 animate-spin text-orange-400" />
            </div>
          )}

          {!loading && error && (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-slate-400 text-center px-4">{error}</p>
            </div>
          )}

          {!loading && !error && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <MessageSquare className="w-10 h-10 text-slate-200" />
              <p className="text-sm text-slate-400 text-center">
                Henüz mesaj yok.<br />İlk mesajı siz gönderin.
              </p>
            </div>
          )}

          {!loading && !error && messages.map((msg) => {
            const isMine = msg.sender_id === currentUser?.id;
            return (
              <div
                key={msg.id}
                className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}
                data-testid={`message-${msg.id}`}
              >
                <div
                  className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${
                    isMine
                      ? 'bg-orange-500 text-white rounded-br-sm'
                      : 'bg-slate-100 text-slate-800 rounded-bl-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                  <p className={`text-[10px] mt-1 ${isMine ? 'text-orange-200' : 'text-slate-400'} text-right`}>
                    {formatTime(msg.created_at)}
                  </p>
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        {!error && (
          <div className="flex items-end gap-2 px-4 py-3 border-t border-slate-100 flex-shrink-0">
            <textarea
              ref={inputRef}
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Mesaj yaz…"
              disabled={loading || sending}
              className="flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-transparent disabled:opacity-50"
              style={{ maxHeight: '120px' }}
              data-testid="messaging-panel-input"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!inputText.trim() || loading || sending}
              className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-orange-500 text-white shadow-sm transition-colors hover:bg-orange-600 disabled:bg-orange-200 disabled:cursor-not-allowed"
              data-testid="messaging-panel-send"
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessagingPanel;
