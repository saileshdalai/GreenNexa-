"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import {
  Bot,
  MessageSquare,
  X,
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Sparkles,
  RefreshCw,
  Database,
  Globe,
  ChevronRight,
  Minus,
} from "lucide-react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  language?: string;
  dataSource?: string;
  suggestedFollowups?: string[];
}

interface AIResponse {
  reply: string;
  language: string;
  detected_intent: string;
  data_source?: string;
  context_used?: Record<string, any>;
  suggested_followups?: string[];
}

interface SuggestionsResponse {
  role: string;
  scope: string;
  suggestions: string[];
}

export default function GreenNexaAssistant() {
  const { user, activeOrgId } = useAuth();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [detectedLang, setDetectedLang] = useState<string>("English");
  const [conversationLanguage, setConversationLanguage] = useState<string>("english");

  // Voice Input (Web Speech Recognition)
  const [isListening, setIsListening] = useState<boolean>(false);
  const recognitionRef = useRef<any>(null);

  // Voice Output (Speech Synthesis)
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen, loading]);

  // Load contextual starter prompt suggestions
  useEffect(() => {
    if (user && isOpen) {
      fetchSuggestions();
    }
  }, [user, isOpen]);

  const fetchSuggestions = async () => {
    try {
      const res = await api.get<SuggestionsResponse>("/api/v1/ai/suggestions");
      if (res && res.suggestions) {
        setSuggestions(res.suggestions);
      }
    } catch (err) {
      // Default fallback prompts
      setSuggestions([
        "Can you explain today's critical anomalies?",
        "Which block has the highest water usage?",
        "ko block re adhika energy usage hauchhi?",
        "କେଉଁ ବ୍ଲକରେ ଅଧିକ ପାଣି ବ୍ୟବହାର ହେଉଛି?",
      ]);
    }
  };

  // Update speech recognition language when conversation language changes
  useEffect(() => {
    if (recognitionRef.current) {
      const langMap: Record<string, string> = {
        english: "en-US",
        hinglish: "hi-IN",
        odia: "or-IN",
        roman_odia: "en-IN",
      };
      recognitionRef.current.lang = langMap[conversationLanguage] || "en-US";
    }
  }, [conversationLanguage]);

  // Initialize Web Speech Recognition
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const rec = new SpeechRecognition();
        rec.continuous = false;
        rec.interimResults = true;
        rec.lang = "en-US";

        rec.onresult = (event: any) => {
          const transcript = Array.from(event.results)
            .map((result: any) => result[0])
            .map((result: any) => result.transcript)
            .join("");
          setInputQuery(transcript);
        };

        rec.onerror = (event: any) => {
          console.warn("Speech recognition error:", event.error);
          setIsListening(false);
        };

        rec.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = rec;
      }
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser version. Please type your query.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        const langMap: Record<string, string> = {
          english: "en-US",
          hinglish: "hi-IN",
          odia: "or-IN",
          roman_odia: "en-IN",
        };
        recognitionRef.current.lang = langMap[conversationLanguage] || "en-US";
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.warn("Speech recognition start failed:", err);
      }
    }
  };

  // Speech Synthesis Control
  const speakText = (msgId: string, text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (speakingMsgId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingMsgId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const langMap: Record<string, string> = {
      english: "en-US",
      hinglish: "hi-IN",
      odia: "or-IN",
      roman_odia: "en-IN",
    };
    utterance.lang = langMap[conversationLanguage] || "en-US";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onend = () => {
      setSpeakingMsgId(null);
    };

    utterance.onerror = () => {
      setSpeakingMsgId(null);
    };

    setSpeakingMsgId(msgId);
    window.speechSynthesis.speak(utterance);
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || loading) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setLoading(true);

    // Stop listening if active
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    try {
      // Build history payloads for follow-up conversational context
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await api.post<AIResponse>("/api/v1/ai/chat", {
        message: query,
        session_history: historyPayload,
        conversation_language: conversationLanguage,
      });

      if (res.language) {
        const langMap: Record<string, string> = {
          english: "English",
          hinglish: "Hinglish",
          odia: "Odia (ଓଡ଼ିଆ)",
          roman_odia: "Roman Odia",
        };
        setDetectedLang(langMap[res.language] || res.language);
      }

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: "assistant",
        content: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        language: res.language,
        dataSource: res.data_source,
        suggestedFollowups: res.suggested_followups,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an issue retrieving telemetry data. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        dataSource: "Error Handler",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChatSession = () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setSpeakingMsgId(null);
    setMessages([]);
  };

  if (!user) return null;

  return (
    <>
      {/* Floating Assistant Trigger Launcher */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "14px 20px",
            borderRadius: "50px",
            background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
            color: "#ffffff",
            border: "none",
            boxShadow: "0 8px 24px rgba(16, 185, 129, 0.35)",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "15px",
            transition: "all 0.2s ease-in-out",
          }}
          className="hover-lift"
        >
          <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
            <Bot size={22} />
            <span
              style={{
                position: "absolute",
                top: "-2px",
                right: "-2px",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#6ee7b7",
                boxShadow: "0 0 8px #6ee7b7",
              }}
            />
          </div>
          <span>GreenNexa AI</span>
          <Sparkles size={16} style={{ opacity: 0.9 }} />
        </button>
      )}

      {/* Expandable Assistant Drawer Panel */}
      {isOpen && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            width: "420px",
            maxWidth: "calc(100vw - 32px)",
            height: "640px",
            maxHeight: "calc(100vh - 48px)",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
            background: "var(--clr-surface)",
            borderRadius: "20px",
            boxShadow: "0 20px 50px rgba(0, 0, 0, 0.25), 0 0 0 1px var(--clr-border)",
            overflow: "hidden",
            transition: "all 0.3s ease",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "16px 20px",
              background: "linear-gradient(135deg, #064e3b 0%, #047857 100%)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(255, 255, 255, 0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Bot size={20} color="#ffffff" />
              </div>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 800, margin: 0, color: "#ffffff" }}>
                  GreenNexa AI
                </h3>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "rgba(255, 255, 255, 0.85)" }}>
                  <span>{user.role === "SUPER_ADMIN" ? "Platform Overview Scope" : `Org: ${activeOrgId || "Authenticated"}`}</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <button
                onClick={clearChatSession}
                title="Clear Chat History"
                style={{ background: "none", border: "none", color: "rgba(255, 255, 255, 0.8)", cursor: "pointer", padding: "6px" }}
              >
                <RefreshCw size={16} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Minimize Assistant"
                style={{ background: "none", border: "none", color: "rgba(255, 255, 255, 0.8)", cursor: "pointer", padding: "6px" }}
              >
                <Minus size={18} />
              </button>
            </div>
          </div>

          {/* Conversation Language Selector Bar */}
          <div
            style={{
              padding: "8px 16px",
              background: "var(--clr-surface-2)",
              borderBottom: "1px solid var(--clr-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "12px",
            }}
          >
            <label htmlFor="conversation-language-select" style={{ fontWeight: 600, color: "var(--clr-text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
              <Globe size={14} color="var(--clr-primary)" />
              <span>Conversation Language:</span>
            </label>
            <select
              id="conversation-language-select"
              aria-label="Conversation Language"
              value={conversationLanguage}
              onChange={(e) => setConversationLanguage(e.target.value)}
              style={{
                padding: "4px 8px",
                borderRadius: "6px",
                border: "1px solid var(--clr-border)",
                background: "var(--clr-surface)",
                color: "var(--clr-text-primary)",
                fontSize: "12px",
                fontWeight: 600,
                outline: "none",
                cursor: "pointer",
              }}
            >
              <option value="english">English</option>
              <option value="hinglish">Hinglish</option>
              <option value="odia">Odia (ଓଡ଼ିଆ)</option>
              <option value="roman_odia">Roman Odia</option>
            </select>
          </div>

          {/* Chat Messages Body */}
          <div
            style={{
              flex: 1,
              padding: "16px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
              background: "var(--clr-bg)",
            }}
          >
            {messages.length === 0 && (
              <div style={{ padding: "12px 4px" }}>
                <div
                  style={{
                    padding: "16px",
                    borderRadius: "14px",
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    marginBottom: "16px",
                  }}
                >
                  <h4 style={{ fontSize: "14px", fontWeight: 700, margin: "0 0 6px 0", color: "var(--clr-text-primary)" }}>
                    👋 Welcome to GreenNexa AI!
                  </h4>
                  <p style={{ fontSize: "12.5px", color: "var(--clr-text-secondary)", margin: 0, lineHeight: 1.5 }}>
                    Ask queries in <strong>English</strong>, <strong>Hinglish</strong>, <strong>Odia (ଓଡ଼ିଆ)</strong>, or <strong>Roman Odia</strong>. Grounded 100% in real telemetry data with zero external API fees.
                  </p>
                </div>

                {suggestions.length > 0 && (
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--clr-text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      Suggested Questions:
                    </span>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
                      {suggestions.map((s, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(s)}
                          style={{
                            textAlign: "left",
                            padding: "10px 14px",
                            borderRadius: "10px",
                            background: "var(--clr-surface)",
                            border: "1px solid var(--clr-border)",
                            color: "var(--clr-text-primary)",
                            fontSize: "12.5px",
                            fontWeight: 500,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                          }}
                        >
                          <span>{s}</span>
                          <ChevronRight size={14} color="var(--clr-text-muted)" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: m.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "85%",
                    padding: "12px 16px",
                    borderRadius: m.role === "user" ? "16px 16px 2px 16px" : "16px 16px 16px 2px",
                    background: m.role === "user" ? "var(--clr-primary)" : "var(--clr-surface)",
                    color: m.role === "user" ? "#ffffff" : "var(--clr-text-primary)",
                    border: m.role === "user" ? "none" : "1px solid var(--clr-border)",
                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
                    fontSize: "13px",
                    lineHeight: 1.55,
                    whiteSpace: "pre-line",
                  }}
                >
                  <div>{m.content}</div>

                  {m.dataSource && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        marginTop: "8px",
                        fontSize: "10.5px",
                        color: m.role === "user" ? "rgba(255,255,255,0.8)" : "var(--clr-text-muted)",
                        fontWeight: 600,
                      }}
                    >
                      <Database size={11} />
                      <span>{m.dataSource}</span>
                    </div>
                  )}
                </div>

                {/* Controls for Assistant Speech & Timestamp */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    marginTop: "4px",
                    fontSize: "10px",
                    color: "var(--clr-text-muted)",
                    padding: "0 4px",
                  }}
                >
                  <span>{m.timestamp}</span>
                  {m.role === "assistant" && (
                    <button
                      onClick={() => speakText(m.id, m.content)}
                      style={{
                        background: "none",
                        border: "none",
                        color: speakingMsgId === m.id ? "var(--clr-primary)" : "var(--clr-text-muted)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "3px",
                        fontWeight: 600,
                      }}
                    >
                      {speakingMsgId === m.id ? <VolumeX size={12} /> : <Volume2 size={12} />}
                      <span>{speakingMsgId === m.id ? "Stop Voice" : "Read Aloud"}</span>
                    </button>
                  )}
                </div>

                {/* Followup suggestion chips under response */}
                {m.suggestedFollowups && m.suggestedFollowups.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px", maxWidth: "90%" }}>
                    {m.suggestedFollowups.map((f, fIdx) => (
                      <button
                        key={fIdx}
                        onClick={() => handleSendMessage(f)}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "14px",
                          background: "var(--clr-surface-2)",
                          border: "1px solid var(--clr-border)",
                          color: "var(--clr-primary-dark)",
                          fontSize: "11.5px",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        + {f}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "var(--clr-text-muted)", fontSize: "12px", padding: "8px" }}>
                <Bot size={16} className="spin" color="var(--clr-primary)" />
                <span>Analyzing telemetry data...</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Listening Pulse Banner */}
          {isListening && (
            <div
              style={{
                padding: "8px 16px",
                background: "#fef2f2",
                borderTop: "1px solid #fecaca",
                color: "#dc2626",
                fontSize: "12px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444" }} className="pulse" />
                <span>Listening ({conversationLanguage})... speak your query now</span>
              </div>
              <button
                onClick={toggleListening}
                style={{ background: "none", border: "none", color: "#dc2626", fontWeight: 700, cursor: "pointer" }}
              >
                Stop
              </button>
            </div>
          )}

          {/* Input Footer */}
          <div style={{ padding: "12px 16px", background: "var(--clr-surface)", borderTop: "1px solid var(--clr-border)" }}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              <input
                type="text"
                placeholder="Ask in English, Hinglish, Odia, or Roman Odia..."
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "1px solid var(--clr-border)",
                  background: "var(--clr-bg)",
                  color: "var(--clr-text-primary)",
                  fontSize: "13px",
                  outline: "none",
                }}
              />

              <button
                type="button"
                onClick={toggleListening}
                title={isListening ? "Stop Voice Input" : "Voice Input (Speech Recognition)"}
                style={{
                  padding: "10px",
                  borderRadius: "10px",
                  border: "1px solid var(--clr-border)",
                  background: isListening ? "#fee2e2" : "var(--clr-surface-2)",
                  color: isListening ? "#dc2626" : "var(--clr-text-secondary)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>

              <button
                type="submit"
                disabled={loading || !inputQuery.trim()}
                style={{
                  padding: "10px 14px",
                  borderRadius: "10px",
                  border: "none",
                  background: "var(--clr-primary)",
                  color: "#ffffff",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: loading || !inputQuery.trim() ? 0.6 : 1,
                }}
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
