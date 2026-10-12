import { useEffect, useState } from 'react'
import { accountApi } from '../../services/api'
import type { ResetPreview } from '../../types'

const CONFIRM_PHRASE = 'RESET MY DATA'

const RESET_ROWS: { key: keyof ResetPreview; label: string }[] = [
  { key: 'practice_sessions', label: 'Practice sessions' },
  { key: 'practice_answers', label: 'Practice answers' },
  { key: 'attempts', label: 'Assessment attempts' },
  { key: 'attempt_answers', label: 'Assessment answers' },
  { key: 'coding_submissions', label: 'Coding submissions' },
  { key: 'xp_transactions', label: 'XP ledger entries' },
  { key: 'badges', label: 'Earned badges' },
  { key: 'bookmarks', label: 'Saved bookmarks' },
  { key: 'missions', label: 'Mission records' },
  { key: 'roadmaps', label: 'Roadmaps (with all items)' },
  { key: 'recommendations', label: 'Recommendations' },
  { key: 'topic_performance_rows', label: 'Topic performance rows' },
  { key: 'performance_snapshots', label: 'Performance snapshots' },
  { key: 'ai_answer_logs', label: 'AI quiz answers' },
  { key: 'activity_events', label: 'Activity events' },
  { key: 'leaderboard_entries', label: 'Leaderboard entries' },
]

export default function AccountSettingsPage() {
  const [preview, setPreview] = useState<ResetPreview | null>(null)
  const [previewError, setPreviewError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  useEffect(() => {
    accountApi
      .resetPreview()
      .then((r) => setPreview(r.data.data))
      .catch((err) => setPreviewError(err.response?.data?.message || 'Could not load reset summary'))
  }, [])

  const anythingToDelete = preview ? Object.values(preview).some((v) => v > 0) : false

  const openModal = () => {
    setStep(1)
    setPassword('')
    setConfirmation('')
    setError('')
    setModalOpen(true)
  }

  const closeModal = () => {
    if (busy) return
    setModalOpen(false)
    setStep(1)
  }

  const executeReset = async () => {
    setBusy(true)
    setError('')
    try {
      await accountApi.reset({ password, confirmation })
      setDone(true)
      setModalOpen(false)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Reset failed')
    } finally {
      setBusy(false)
    }
  }

  const totalRows = preview
    ? Object.values(preview).reduce((sum, n) => sum + n, 0)
    : 0

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Account settings</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your learning data.</p>
      </div>

      {done && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl p-4">
          <p className="font-medium">Your learning data has been reset.</p>
          <p className="text-sm mt-1">
            Your account is untouched — you can start fresh right now.{' '}
            <a href="/student/dashboard" className="underline font-medium">Go to dashboard →</a>
          </p>
        </div>
      )}

      {/* What will be deleted */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-1">What resetting deletes</h2>
        <p className="text-xs text-slate-500 mb-4">
          Everything is wiped in one irreversible action. Your login, email, password and role are
          NOT affected.
        </p>
        {previewError && (
          <div className="bg-red-50 text-red-600 rounded-lg p-3 text-sm">{previewError}</div>
        )}
        {!previewError && !preview && <div className="text-sm text-slate-400 py-4">Loading…</div>}
        {preview && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
            {RESET_ROWS.map((r) => (
              <div key={r.key} className="flex justify-between bg-slate-50 rounded-lg px-3 py-2">
                <span className="text-slate-600 truncate">{r.label}</span>
                <span className="font-medium text-slate-800 ml-2">{preview[r.key]}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* DANGER ZONE — GitHub style */}
      <section
        aria-labelledby="danger-zone-heading"
        className="rounded-xl border border-red-300 overflow-hidden"
      >
        <h2 id="danger-zone-heading" className="sr-only">Danger zone</h2>
        <div className="bg-red-50 px-5 py-3 border-b border-red-200">
          <span className="text-sm font-semibold text-red-700">Danger Zone</span>
          <span className="text-xs text-red-500 ml-2">Irreversible actions</span>
        </div>
        <div className="bg-white px-5 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-800">
              Reset all learning data
              {preview && totalRows > 0 && (
                <span className="text-red-600 font-semibold"> — {totalRows} records</span>
              )}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Deletes practice, assessments, coding submissions, XP, badges, streaks, roadmap,
              bookmarks and history for this account. The account itself is kept.{' '}
              <strong className="text-red-600">This cannot be undone.</strong>
            </p>
          </div>
          <button
            type="button"
            onClick={openModal}
            disabled={!preview || !anythingToDelete}
            className="shrink-0 px-4 py-2 rounded-lg border border-red-300 text-red-600 text-sm font-medium hover:bg-red-600 hover:text-white hover:border-red-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-red-600"
          >
            Reset all learning data
          </button>
          {!anythingToDelete && preview && (
            <p className="text-xs text-slate-400 w-full">Nothing to reset — your slate is already clean.</p>
          )}
      </div>
      </section>

      {/* Confirmation modal — two steps */}
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="reset-modal-title"
          onKeyDown={(e) => e.key === 'Escape' && closeModal()}
        >
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4">
            <div>
              <h3 id="reset-modal-title" className="text-lg font-bold text-red-600">
                {step === 1 ? 'Are you absolutely sure?' : 'Confirm with your password'}
              </h3>
              <p className="text-sm text-slate-600 mt-2">
                {step === 1 ? (
                  <>
                    This will permanently delete{' '}
                    <strong>{totalRows} records</strong> of learning data — XP, badges, streaks,
                    history, everything. <strong className="text-red-600">It cannot be undone.</strong>
                  </>
                ) : (
                  'Type your password and the phrase below to confirm.'
                )}
              </p>
            </div>

            {step === 1 ? (
              <div className="flex justify-end gap-2">
                <button type="button" onClick={closeModal}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50">
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700"
                >
                  I understand, continue
                </button>
              </div>
            ) : (
              <form
                onSubmit={(e) => { e.preventDefault(); executeReset() }}
                className="space-y-4"
              >
                <div>
                  <label htmlFor="reset-password" className="block text-sm font-medium text-slate-700 mb-1">
                    Your password
                  </label>
                  <input
                    id="reset-password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="reset-phrase" className="block text-sm font-medium text-slate-700 mb-1">
                    Type{' '}
                    <code className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-mono text-xs">
                      {CONFIRM_PHRASE}
                    </code>{' '}
                    to confirm
                  </label>
                  <input
                    id="reset-phrase"
                    type="text"
                    value={confirmation}
                    onChange={(e) => setConfirmation(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500"
                    required
                  />
                </div>

                {error && (
                  <div className="bg-red-50 text-red-600 rounded-lg p-3 text-sm" role="alert">{error}</div>
                )}

                <div className="flex justify-end gap-2 pt-1">
                  <button type="button" onClick={closeModal} disabled={busy}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50">
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={busy || confirmation !== CONFIRM_PHRASE || password.length === 0}
                    className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {busy ? 'Resetting…' : 'Delete everything'}
                  </button>
                  <button type="button" onClick={() => setStep(1)} disabled={busy}
                    className="px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-700 disabled:opacity-50">
                    ← Back
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
