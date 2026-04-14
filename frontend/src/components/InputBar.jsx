/**
 * InputBar.jsx
 * ------------
 * The text input area at the bottom of the chat.
 *
 * Features:
 *  - Auto-grows textarea (up to ~4 lines)
 *  - Enter to submit, Shift+Enter for newline
 *  - Disabled while waiting for the bot response
 *  - Clear chat button
 *
 * Props:
 *   onSend     — callback(text: string)
 *   onClear    — callback() to clear chat history
 *   isLoading  — bool, disables send while waiting
 */

import React, { useState, useRef, useEffect } from 'react'

// Send icon SVG (paper plane)
function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  )
}

export default function InputBar({ onSend, onClear, isLoading }) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize the textarea based on content
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [text])

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setText('')
    // Reset height after clear
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    // Enter without Shift → send message
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="input-bar">
      <textarea
        ref={textareaRef}
        id="chat-input"
        className="chat-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about Amenify services…"
        rows={1}
        disabled={isLoading}
        aria-label="Type your message"
        autoComplete="off"
        spellCheck="true"
      />

      {/* Clear chat button — only show when there's something to clear */}
      <button
        className="clear-btn"
        onClick={onClear}
        title="Clear chat history"
        aria-label="Clear chat"
        tabIndex={-1}
      >
        Clear
      </button>

      {/* Send button */}
      <button
        id="send-button"
        className="send-button"
        onClick={handleSubmit}
        disabled={isLoading || !text.trim()}
        aria-label="Send message"
        title="Send (Enter)"
      >
        <SendIcon />
      </button>
    </div>
  )
}
