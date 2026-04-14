/**
 * MessageBubble.jsx
 * -----------------
 * Renders a single message in the chat window.
 *
 * Props:
 *   role    — 'user' | 'assistant'
 *   content — the message text (may contain markdown for assistant)
 *   sources — array of { url, title } (only for assistant messages)
 *   isError — true if the backend returned an error
 */

import React from 'react'
import ReactMarkdown from 'react-markdown'

// Format a Date to a short HH:MM string
function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function MessageBubble({ role, content, sources = [], isError = false, timestamp }) {
  const isUser = role === 'user'
  const time = timestamp ? formatTime(new Date(timestamp)) : formatTime(new Date())

  return (
    <div className={`message-row ${isUser ? 'user' : 'bot'}`}>
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? 'user' : 'bot'}`}>
        {isUser ? '👤' : '🏠'}
      </div>

      {/* Content column */}
      <div className="message-content">
        {/* Text bubble */}
        <div className={`bubble ${isUser ? 'user' : 'bot'} ${isError ? 'error' : ''}`}>
          {isUser ? (
            // User messages are plain text — no markdown needed
            <span>{content}</span>
          ) : (
            // Assistant messages may use markdown (bullet lists, bold, etc.)
            <ReactMarkdown>{content}</ReactMarkdown>
          )}
        </div>

        {/* Source chips — only for assistant messages with sources */}
        {!isUser && sources.length > 0 && (
          <div className="sources" aria-label="Sources">
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', alignSelf: 'center' }}>
              Sources:
            </span>
            {sources.map((src, idx) => (
              <a
                key={idx}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="source-chip"
                title={src.url}
              >
                🔗 {src.title}
              </a>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="message-time">{time}</span>
      </div>
    </div>
  )
}
