import { useState, useRef, useEffect } from 'react'
import { api } from '../lib/api'
import type { CopilotResponse } from '../types'
import { Send, Bot, User, Sparkles } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  confidence?: number
  sources?: { type: string; id: number; relevance: number }[]
  followUps?: string[]
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  let listItems: string[] = []
  let listOrdered = false
  let listKey = 0

  const flushList = () => {
    if (listItems.length > 0) {
      const Tag = listOrdered ? 'ol' : 'ul'
      const cls = listOrdered
        ? 'list-decimal list-inside space-y-1 my-2 text-sm'
        : 'list-disc list-inside space-y-1 my-2 text-sm'
      elements.push(
        <Tag key={`list-${listKey++}`} className={cls}>
          {listItems.map((item, i) => (
            <li key={i} className="text-surface-700 dark:text-surface-300">{renderInline(item)}</li>
          ))}
        </Tag>
      )
      listItems = []
      listOrdered = false
    }
  }

  const flushTable = (tableLines: string[]) => {
    if (tableLines.length < 2) return
    const headerCells = tableLines[0].split('|').map(c => c.trim()).filter(Boolean)
    const rows = tableLines.slice(2).map(row =>
      row.split('|').map(c => c.trim()).filter(Boolean)
    )
    elements.push(
      <div key={`table-${listKey++}`} className="overflow-x-auto my-3">
        <table className="w-full text-sm border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
          <thead>
            <tr className="bg-surface-50 dark:bg-surface-800">
              {headerCells.map((cell, i) => (
                <th key={i} className="px-3 py-2 text-left font-medium text-surface-700 dark:text-surface-300 border-b border-surface-200 dark:border-surface-700">{renderInline(cell)}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
            {rows.map((row, ri) => (
              <tr key={ri} className="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-2 text-surface-700 dark:text-surface-300">{renderInline(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const renderInline = (t: string) => {
    const parts: (string | JSX.Element)[] = []
    // Match: **bold**, *italic*, ~~strike~~, `code`, ***bold italic***
    const regex = /\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|~~(.+?)~~|`(.+?)`/g
    let lastIdx = 0
    let match
    while ((match = regex.exec(t)) !== null) {
      if (match.index > lastIdx) parts.push(t.slice(lastIdx, match.index))
      if (match[1]) parts.push(<strong key={match.index} className="font-semibold italic">{match[1]}</strong>)
      else if (match[2]) parts.push(<strong key={match.index} className="font-semibold">{match[2]}</strong>)
      else if (match[3]) parts.push(<em key={match.index} className="italic text-surface-600 dark:text-surface-400">{match[3]}</em>)
      else if (match[4]) parts.push(<del key={match.index} className="line-through text-surface-400">{match[4]}</del>)
      else if (match[5]) parts.push(<code key={match.index} className="px-1.5 py-0.5 bg-surface-200 dark:bg-surface-700 rounded text-xs font-mono">{match[5]}</code>)
      lastIdx = match.index + match[0].length
    }
    if (lastIdx < t.length) parts.push(t.slice(lastIdx))
    return parts
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    // Table: | col | col |
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      const tableLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim())
        i++
      }
      flushList()
      flushTable(tableLines)
      continue
    }

    // Empty line
    if (!trimmed) {
      flushList()
      i++
      continue
    }

    // Horizontal rule: --- or *** or ___
    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushList()
      elements.push(<hr key={`hr-${listKey++}`} className="my-3 border-surface-200 dark:border-surface-700" />)
      i++
      continue
    }

    // Headers: # through ######
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.+)/)
    if (headerMatch) {
      flushList()
      const level = headerMatch[1].length
      const sizes: Record<number, string> = {
        1: 'text-xl font-bold mt-4 mb-2',
        2: 'text-lg font-bold mt-3 mb-2',
        3: 'text-base font-semibold mt-3 mb-1',
        4: 'text-sm font-semibold mt-2 mb-1',
        5: 'text-sm font-medium mt-2 mb-1',
        6: 'text-xs font-medium mt-2 mb-1 uppercase tracking-wide',
      }
      elements.push(<p key={`h-${listKey++}`} className={`${sizes[level] || sizes[3]} text-surface-900 dark:text-white`}>{renderInline(headerMatch[2])}</p>)
      i++
      continue
    }

    // Blockquote: > text
    const quoteMatch = trimmed.match(/^>\s*(.+)/)
    if (quoteMatch) {
      flushList()
      elements.push(
        <blockquote key={`bq-${listKey++}`} className="border-l-3 border-brand-400 pl-3 my-2 text-sm italic text-surface-600 dark:text-surface-400">
          {renderInline(quoteMatch[1])}
        </blockquote>
      )
      i++
      continue
    }

    // Bullet: -
    const bulletMatch = trimmed.match(/^-\s+(.+)/)
    if (bulletMatch) {
      listOrdered = false
      listItems.push(bulletMatch[1])
      i++
      continue
    }

    // Numbered list: 1. 2. etc
    const numMatch = trimmed.match(/^\d+[.)]\s+(.+)/)
    if (numMatch) {
      listOrdered = true
      listItems.push(numMatch[1])
      i++
      continue
    }

    flushList()
    elements.push(<p key={`p-${listKey++}`} className="text-sm leading-relaxed my-1.5 text-surface-700 dark:text-surface-300">{renderInline(trimmed)}</p>)
    i++
  }

  flushList()
  return elements
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [loading])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const res: CopilotResponse = await api.askCopilot(question, conversationId)
      setConversationId(res.conversation_id)
      setMessages(prev => [...prev, {
        role: 'assistant', content: res.answer,
        confidence: res.confidence, sources: res.sources,
        followUps: res.suggested_follow_ups,
      }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error processing your request.' }])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">AI Copilot</h1>
        <p className="text-surface-600 dark:text-surface-400 mt-1">Ask business questions about your competitive landscape</p>
      </div>

      <div className="flex-1 overflow-y-auto bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-brand-300 dark:text-brand-600 mb-4" />
            <h2 className="text-xl font-semibold text-surface-900 dark:text-white mb-2">How can I help?</h2>
            <p className="text-surface-500 max-w-md">Ask me about competitors, pricing, growth, risks, opportunities, or market trends.</p>
            <div className="flex flex-wrap gap-2 mt-6 justify-center">
              {["Which competitors expanded fastest?", "What pricing gaps exist in Chennai?", "Who are our biggest risks?", "Summarize the latest market trends"].map(q => (
                <button key={q} onClick={() => { setInput(q); inputRef.current?.focus() }}
                  className="px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg text-sm text-surface-700 dark:text-surface-300 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-900/20 dark:hover:text-brand-400 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0 mt-1">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
              </div>
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-brand-500 text-white rounded-br-md'
                : 'bg-surface-100 dark:bg-surface-800 text-surface-900 dark:text-white rounded-bl-md'
            }`}>
              {msg.role === 'assistant' ? (
                <div className="space-y-0">{renderMarkdown(msg.content)}</div>
              ) : (
                <p className="text-sm">{msg.content}</p>
              )}
              {msg.role === 'assistant' && msg.confidence !== undefined && (
                <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-700 flex items-center gap-3 text-xs text-surface-500">
                  <span className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${msg.confidence >= 0.7 ? 'bg-green-500' : msg.confidence >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                    {Math.round(msg.confidence * 100)}% confidence
                  </span>
                  {msg.sources && msg.sources.length > 0 && <span>{msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}</span>}
                </div>
              )}
              {msg.role === 'assistant' && msg.followUps && msg.followUps.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.followUps.map((fu, j) => (
                    <button key={j} onClick={() => { setInput(fu); inputRef.current?.focus() }}
                      className="text-xs px-2.5 py-1 bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 rounded-full hover:bg-brand-100 dark:hover:bg-brand-900/30 transition-colors">
                      {fu}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-surface-200 dark:bg-surface-700 flex items-center justify-center flex-shrink-0 mt-1">
                <User className="w-4 h-4 text-surface-500" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400 animate-pulse" />
            </div>
            <div className="bg-surface-100 dark:bg-surface-800 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="mt-3 flex gap-2">
        <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
          placeholder="Ask a question..." disabled={loading}
          className="flex-1 rounded-xl border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-4 py-3 text-sm text-surface-900 dark:text-white focus:ring-2 focus:ring-brand-500 outline-none disabled:opacity-50 transition-shadow" />
        <button onClick={sendMessage} disabled={loading || !input.trim()}
          className="bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white px-5 py-3 rounded-xl font-medium flex items-center gap-2 transition-colors">
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
