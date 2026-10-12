import { useEffect, useRef, useState } from 'react'
import { chatApi } from '../../services/api'
import type { ChatMessage } from '../../types'

const SUGGESTIONS = [
  'How do I prepare for aptitude tests?',
  'Explain time complexity with an example',
  'What is the TCS NQT pattern?',
  'Tips to improve my coding speed',
]

function ChatbotPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Hi! I'm your SkillSprint study buddy. Ask me anything — aptitude doubts, coding concepts, interview prep, study plans, or general academic questions.",
    },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || sending) return

    const history = messages
      .filter((m) => !(m.role === 'assistant' && messages.indexOf(m) === 0))
      .slice(-10)

    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    setSending(true)
    setError('')

    try {
      const res = await chatApi.send(message, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.data.reply }])
    } catch (err) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message || ''
      if ((err as { response?: { status?: number } })?.response?.status === 429) {
        setError('AI limit reached (10 messages/minute). Please wait a moment and try again.')
      } else if ((err as { response?: { status?: number } })?.response?.status === 503) {
        setError('AI service is unavailable right now. Please try again shortly.')
      } else {
        setError(msg || 'Failed to get a reply. Please try again.')
      }
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    void send(input)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-9rem)] max-w-3xl mx-auto">
      <div className="mb-3">
        <h1 className="text-2xl font-bold text-slate-800">Study Chatbot</h1>
        <p className="text-sm text-slate-500">
          Ask anything about your placement preparation — powered by Gemini
        </p>
      </div>

      <div className="flex-1 overflow-y-auto bg-white border border-slate-200 rounded-xl p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-slate-100 text-slate-800 rounded-bl-sm'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-slate-100 text-slate-500 rounded-2xl rounded-bl-sm px-4 py-2 text-sm">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}

      {messages.length === 1 && !sending && (
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => void send(s)}
              className="text-xs bg-white border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50 text-slate-600 rounded-full px-3 py-1.5 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything…"
          maxLength={2000}
          disabled={sending}
          className="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="bg-indigo-600 text-white text-sm font-medium rounded-xl px-5 py-2.5 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  )
}

export default ChatbotPage
