/**
 * ChatWindow.jsx
 * --------------
 * Scrollable message list.
 * Shows the welcome screen when there are no messages yet.
 * Auto-scrolls to the bottom on new messages.
 *
 * Props:
 *   messages      — array of { id, role, content, sources, isError, timestamp }
 *   isLoading     — bool, shows typing indicator when true
 *   onSuggestion  — callback(text) when a suggestion chip is clicked
 */

import React, { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble.jsx'

// Quick-start suggestion questions displayed on the welcome screen
const SUGGESTIONS = [
  'What services does Amenify offer?',
  'Are service pros background-checked?',
  'How do I book a cleaning service?',
  'Does Amenify offer dog walking?',
  'What is Amenify Cash?',
  'How do I cancel or reschedule?',
]

function WelcomeScreen({ onSuggestion }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">🏠</div>
      <h1 className="welcome-title">Amenify Support Assistant</h1>
      <p className="welcome-subtitle">
        Ask me anything about Amenify's services — cleaning, handyman, chores,
        dog walking, food delivery, and more.
      </p>
      <div className="suggested-questions">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            className="suggestion-btn"
            onClick={() => onSuggestion(q)}
            id={`suggestion-${q.replace(/\s+/g, '-').toLowerCase().slice(0, 30)}`}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="message-row bot">
      <div className="message-avatar bot">🏠</div>
      <div className="message-content">
        <div className="typing-indicator" aria-label="Amenify is typing">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, isLoading, onSuggestion }) {
  const bottomRef = useRef(null)

  // Auto-scroll to the latest message whenever messages or loading state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="chat-window" role="log" aria-live="polite" aria-label="Chat messages">
      {messages.length === 0 ? (
        <WelcomeScreen onSuggestion={onSuggestion} />
      ) : (
        <>
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              sources={msg.sources || []}
              isError={msg.isError || false}
              timestamp={msg.timestamp}
            />
          ))}

          {/* Typing indicator while waiting for a response */}
          {isLoading && <TypingIndicator />}
        </>
      )}
      {/* Invisible anchor for auto-scroll */}
      <div ref={bottomRef} />
    </div>
  )
}
