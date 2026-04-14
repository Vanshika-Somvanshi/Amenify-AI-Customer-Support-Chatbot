/**
 * App.jsx
 * -------
 * Root component. Owns all state and the API call logic.
 *
 * State:
 *   messages — array of message objects stored in sessionStorage
 *              (cleared when the browser tab is closed)
 *   isLoading — true while waiting for a backend response
 *
 * Session history strategy:
 *   • The full message list is kept in React state for rendering
 *   • A "history" array (role + content only, no UI fields) is derived
 *     from messages and sent to the backend on every request
 *   • sessionStorage persists messages for the duration of the browser session
 *
 * API:
 *   VITE_API_URL environment variable → falls back to localhost:8000 in dev
 */

import React, { useState, useEffect, useCallback } from 'react'
import ChatWindow from './components/ChatWindow.jsx'
import InputBar   from './components/InputBar.jsx'

// Backend URL — set VITE_API_URL in Vercel env vars after deploying to Render
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// sessionStorage key for persisting messages across page refreshes
// (cleared automatically when the browser tab is closed)
const SESSION_KEY = 'amenify_chat_messages'

// Generate a simple unique ID for each message
let _idCounter = 0
function nextId() { return `msg_${Date.now()}_${++_idCounter}` }

export default function App() {
  // ── Load messages from sessionStorage on first render ─────────────────────
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_KEY)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  const [isLoading, setIsLoading] = useState(false)

  // ── Persist messages to sessionStorage on every change ─────────────────────
  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(messages))
    } catch {
      // sessionStorage may be unavailable in some private-browsing contexts
    }
  }, [messages])

  // ── Helper: add a message to the list ──────────────────────────────────────
  const addMessage = useCallback((role, content, extras = {}) => {
    const msg = {
      id:        nextId(),
      role,
      content,
      timestamp: Date.now(),
      sources:   [],
      isError:   false,
      ...extras,
    }
    setMessages((prev) => [...prev, msg])
    return msg
  }, [])

  // ── Send a message to the backend ──────────────────────────────────────────
  const handleSend = useCallback(async (text) => {
    // 1. Immediately add the user message to the UI
    addMessage('user', text)
    setIsLoading(true)

    // 2. Build chat history to send (role + content only, last 10 turns max)
    //    We snapshot `messages` before the new user message is appended
    const historyToSend = messages
      .slice(-10)  // keep last 10 turns to stay within token limits
      .map(({ role, content }) => ({ role, content }))

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: historyToSend,
        }),
      })

      if (!response.ok) {
        const errText = await response.text()
        throw new Error(`Server error ${response.status}: ${errText}`)
      }

      const data = await response.json()

      // 3. Add the assistant's grounded answer
      addMessage('assistant', data.answer, { sources: data.sources || [] })

    } catch (err) {
      console.error('Chat API error:', err)
      addMessage('assistant', `Sorry, I couldn't reach the Amenify support service. Please try again in a moment.`, {
        isError: true,
      })
    } finally {
      setIsLoading(false)
    }
  }, [messages, addMessage])

  // ── Handle suggestion chip clicks from the welcome screen ─────────────────
  const handleSuggestion = useCallback((text) => {
    handleSend(text)
  }, [handleSend])

  // ── Clear chat ────────────────────────────────────────────────────────────
  const handleClear = useCallback(() => {
    setMessages([])
    sessionStorage.removeItem(SESSION_KEY)
  }, [])

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">🏠</div>
        <div className="header-info">
          <div className="header-title">Amenify Support</div>
          <div className="header-subtitle">AI-powered · amenify.com knowledge base</div>
        </div>
        <div className="status-badge">
          <div className="status-dot" />
          Online
        </div>
      </header>

      {/* Scrollable message area */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSuggestion={handleSuggestion}
      />

      {/* Input area */}
      <InputBar
        onSend={handleSend}
        onClear={handleClear}
        isLoading={isLoading}
      />

      {/* Footer */}
      <footer className="footer">
        Answers are sourced exclusively from amenify.com · Powered by Llama 3.3 via Groq
      </footer>
    </div>
  )
}
