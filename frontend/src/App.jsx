import { useState } from 'react'

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 }

const PILL = {
  likely_real: 'green', likely_fabricated: 'red', cannot_verify: 'gray',
  yes: 'green', partial: 'amber', no: 'red',
  accurate: 'green', altered: 'red', not_in_source: 'red', no_quote: 'gray',
}

const label = (s) => s.replace(/_/g, ' ')
const pct = (v) => `${Math.round(v * 100)}%`
const confColor = (v) => (v >= 0.8 ? 'var(--green)' : v >= 0.5 ? 'var(--medium)' : 'var(--high)')

function Pill({ value }) {
  return <span className={`pill ${PILL[value] || 'gray'}`}>{label(value)}</span>
}

function Confidence({ value }) {
  return (
    <div className="conf">
      <div className="conf-track">
        <div className="conf-fill" style={{ width: pct(value), background: confColor(value) }} />
      </div>
      <span className="conf-pct">{pct(value)}</span>
    </div>
  )
}

function FindingCard({ f }) {
  return (
    <div className={`card finding ${f.severity}`}>
      <div className="finding-head">
        <span className={`badge ${f.severity}`}>{f.severity}</span>
        <span className="badge type">{label(f.type)}</span>
        <span className="finding-title">{f.summary}</span>
      </div>
      <div className="grid2">
        <div><div className="label">Motion claims</div><div className="value">{f.claim}</div></div>
        <div><div className="label">Record / law says</div><div className="value">{f.evidence}</div></div>
      </div>
      <Confidence value={f.confidence} />
      {f.confidence_reasoning && <div className="reasoning">{f.confidence_reasoning}</div>}
      {f.source_documents?.length > 0 && (
        <div className="chips">
          {f.source_documents.map((s) => <span key={s} className="chip">{label(s)}</span>)}
        </div>
      )}
    </div>
  )
}

function Stat({ num, label: l }) {
  return <div className="stat"><div className="stat-num">{num}</div><div className="stat-label">{l}</div></div>
}

function App() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const response = await fetch('http://localhost:8002/analyze', { method: 'POST' })
      if (!response.ok) throw new Error(`Server responded with ${response.status}`)
      setReport(await response.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const findings = report
    ? [...report.findings].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.confidence - a.confidence)
    : []
  const highCount = findings.filter((f) => f.severity === 'high').length

  return (
    <>
      <header className="header">
        <div className="header-inner">
          <span className="brand-mark">BS</span>
          <div>
            <h1 className="title">BS Detector</h1>
            <p className="subtitle">Legal brief verification pipeline</p>
          </div>
        </div>
      </header>

      <div className="container">
        <button className="btn" onClick={runAnalysis} disabled={loading}>
          {loading && <span className="spinner" />}
          {loading ? 'Analyzing documents...' : 'Run Analysis'}
        </button>

        {error && <div className="error">Error: {error}</div>}
        {report === null && !loading && !error && (
          <p className="hint">Click "Run Analysis" to verify the case documents.</p>
        )}

        {report && (
          <>
            <div className="case-line">{report.case}</div>

            <div className="stats">
              <Stat num={findings.length} label="Findings" />
              <Stat num={highCount} label="High severity" />
              <Stat num={report.citations?.length || 0} label="Citations checked" />
              <Stat num={report.errors?.length || 0} label="Agent errors" />
            </div>

            {report.errors?.length > 0 && (
              <div className="banner">
                <strong>Partial result:</strong> {report.errors.length} agent(s) failed; showing what completed.
                <ul>{report.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </div>
            )}

            {report.judicial_memo && (
              <div className="section">
                <h2>Memo for the Judge</h2>
                <div className="card memo">{report.judicial_memo}</div>
              </div>
            )}

            <div className="section">
              <h2>Findings ({findings.length})</h2>
              {findings.length === 0
                ? <p className="hint">No material verification problems found.</p>
                : findings.map((f) => <FindingCard key={f.id} f={f} />)}
            </div>

            {report.citations?.length > 0 && (
              <div className="section">
                <h2>Citations ({report.citations.length})</h2>
                <div className="card table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Citation</th><th>Exists</th><th>Supports</th><th>Quote</th><th>Conf.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.citations.map((c) => (
                        <tr key={c.citation_id}>
                          <td className="cite-text">{c.citation_text}</td>
                          <td><Pill value={c.exists_verdict} /></td>
                          <td><Pill value={c.supports_proposition} /></td>
                          <td><Pill value={c.quote_accuracy} /></td>
                          <td>{pct(c.confidence)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}

export default App
