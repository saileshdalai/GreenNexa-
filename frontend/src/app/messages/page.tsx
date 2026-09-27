"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { Message, RecipientUser } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { MessageSquare, Send, Inbox, Mail, Plus, X, RefreshCw } from "lucide-react";

export default function MessagesPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [tab, setTab] = useState<"inbox" | "sent">("inbox");
  const [messages, setMessages] = useState<Message[]>([]);
  const [recipients, setRecipients] = useState<RecipientUser[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);

  // Compose Modal State
  const [composeOpen, setComposeOpen] = useState<boolean>(false);
  const [recipientId, setRecipientId] = useState<string>("");
  const [subject, setSubject] = useState<string>("");
  const [body, setBody] = useState<string>("");
  const [sending, setSending] = useState<boolean>(false);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const endpoint = tab === "inbox" ? "/api/v1/messages/inbox" : "/api/v1/messages/sent";
      const res = await api.get<Message[]>(endpoint);
      setMessages(res);
    } catch {
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const loadRecipients = async () => {
    try {
      const res = await api.get<RecipientUser[]>("/api/v1/messages/recipients");
      setRecipients(res);
    } catch {}
  };

  useEffect(() => {
    loadMessages();
  }, [tab]);

  useEffect(() => {
    loadRecipients();
  }, []);

  const openMessageDetail = async (msg: Message) => {
    setSelectedMessage(msg);
    if (tab === "inbox" && !msg.is_read) {
      try {
        await api.patch(`/api/v1/messages/${msg.id}/read`);
        loadMessages();
      } catch {}
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipientId) {
      showToast("Please select a recipient", "error");
      return;
    }
    if (!subject.trim()) {
      showToast("Please enter a subject", "error");
      return;
    }
    if (!body.trim()) {
      showToast("Please enter a message body", "error");
      return;
    }

    setSending(true);
    try {
      await api.post("/api/v1/messages", {
        recipient_id: recipientId,
        subject: subject,
        body: body,
      });
      showToast("Message sent successfully", "success");
      setComposeOpen(false);
      setRecipientId("");
      setSubject("");
      setBody("");
      if (tab === "sent") loadMessages();
    } catch (err: any) {
      showToast(err.message || "Failed to send message", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <MessageSquare color="var(--clr-primary)" /> Internal Messaging
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            In-app communication within GreenNexa organisation boundaries
          </p>
        </div>

        <button
          onClick={() => setComposeOpen(true)}
          className="btn btn-primary"
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <Plus size={16} /> Compose Message
        </button>
      </div>

      {/* Inbox / Sent Tabs */}
      <div className="card" style={{ padding: "12px 20px", marginBottom: "24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setTab("inbox")}
            className={`btn btn-sm ${tab === "inbox" ? "btn-primary" : "btn-outline"}`}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Inbox size={14} /> Inbox
          </button>
          <button
            onClick={() => setTab("sent")}
            className={`btn btn-sm ${tab === "sent" ? "btn-primary" : "btn-outline"}`}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Send size={14} /> Sent
          </button>
        </div>

        <button onClick={loadMessages} className="btn btn-outline btn-sm">
          <RefreshCw size={14} className={loading ? "spin" : ""} />
        </button>
      </div>

      {/* Message List */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "24px" }}>
            <Skeleton height="40px" style={{ marginBottom: "12px" }} />
            <Skeleton height="40px" />
          </div>
        ) : messages.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                onClick={() => openMessageDetail(msg)}
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--clr-border-light)",
                  cursor: "pointer",
                  background: !msg.is_read && tab === "inbox" ? "var(--clr-primary-light)" : "transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "background 0.15s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <Mail size={18} color={!msg.is_read && tab === "inbox" ? "var(--clr-primary)" : "var(--clr-text-muted)"} />
                  <div>
                    <div style={{ fontWeight: !msg.is_read && tab === "inbox" ? 700 : 600, fontSize: "14px", color: "var(--clr-text-primary)" }}>
                      {msg.subject}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
                      {tab === "inbox" ? `From: ${msg.sender_name || msg.sender_id}` : `To: ${msg.recipient_name || msg.recipient_id}`}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  {!msg.is_read && tab === "inbox" && <Badge variant="primary" size="sm">UNREAD</Badge>}
                  <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
                    {new Date(msg.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title={`No ${tab} messages`} description={`Your ${tab} is currently empty.`} />
        )}
      </div>

      {/* Compose Modal */}
      {composeOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div className="card" style={{ maxWidth: "540px", width: "100%", padding: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Compose Internal Message</h2>
              <button onClick={() => setComposeOpen(false)} style={{ border: "none", background: "none", cursor: "pointer" }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSendMessage}>
              <div className="form-group">
                <label className="form-label">Recipient</label>
                <select
                  className="form-input"
                  value={recipientId}
                  onChange={(e) => setRecipientId(e.target.value)}
                >
                  <option value="">Select Recipient...</option>
                  {recipients.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.full_name} ({r.email}) [{r.role}]
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Subject</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Message subject..."
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  maxLength={200}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Message Body</label>
                <textarea
                  className="form-input"
                  placeholder="Write your message here..."
                  rows={5}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "24px" }}>
                <button type="button" onClick={() => setComposeOpen(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" disabled={sending} className="btn btn-primary">
                  {sending ? "Sending..." : "Send Message"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Message Detail Modal */}
      {selectedMessage && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: "20px" }}>
          <div className="card" style={{ maxWidth: "600px", width: "100%", padding: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 700 }}>{selectedMessage.subject}</h2>
              <button onClick={() => setSelectedMessage(null)} style={{ border: "none", background: "none", cursor: "pointer" }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid var(--clr-border-light)" }}>
              <div>From: <strong>{selectedMessage.sender_name || selectedMessage.sender_id}</strong></div>
              <div>To: <strong>{selectedMessage.recipient_name || selectedMessage.recipient_id}</strong></div>
              <div>Sent: {new Date(selectedMessage.created_at).toLocaleString()}</div>
            </div>

            <div style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--clr-text-primary)", whiteSpace: "pre-wrap" }}>
              {selectedMessage.body}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "24px" }}>
              <button onClick={() => setSelectedMessage(null)} className="btn btn-primary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
