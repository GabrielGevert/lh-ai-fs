import { useState } from 'react'

const SEVERITY_COLOR = { high: '#c0392b', medium: '#b9770e', low: '#7f8c8d' }
const VERDICT_COLOR = {
  likely_real: '#1e8449', likely_fabricated: '#c0392b', cannot_verify: '#7f8c8d',
  yes: '#1e8449', partial: '#b9770e', no: '#c0392b',
  accurate: '#1e8449', altered: '#c0392b', not_in_source: '#c0392b', no_quote: '#7f8c8d',
}

const card = { border: '1px solid #e1e4e8', borderRadius: 8, padding: 16, marginBottom: 12, background: '#fff' }
const badge = (bg) => ({ background: bg, color: '#fff', padding: '2px 8px', borderRadius: 12, fontSize: 12, fontWeight: 600 })

function Pill({ text, color }) {
  return <span style={badge(color || '#7f8c8d')}>{text}</span>
}

function ConfidenceBar({ value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: '#eee', borderRadius: 3 }}>
        <div style={{ width: `${Math.round(value * 100)}%`, height: 6, background: '#2c3e50', borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 12, color: '#555', minWidth: 34 }}>{Math.round(value * 100)}%</span>
    </div>
  )
}

function FindingCard({ f }) {
  return (
    <div style={{ ...card, borderLeft: `4px solid ${SEVERITY_COLOR[f.severity] || '#ccc'}` }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
        <Pill text={f.severity} color={SEVERITY_COLOR[f.severity]} />
        <Pill text={f.type.replace(/_/g, ' ')} color="#34495e" />
        <strong style={{ fontSize: 15 }}>{f.summary}</strong>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 8 }}>
        <div><div style={{ fontSize: 12, color: '#888' }}>Motion claims</div><div style={{ fontSize: 14 }}>{f.claim}</div></div>
        <div><div style={{ fontSize: 12, color: '#888' }}>Record / law says</div><div style={{ fontSize: 14 }}>{f.evidence}</div></div>
      </div>
      <ConfidenceBar value={f.confidence} />
      <div style={{ fontSize: 12, color: '#777', marginTop: 6, fontStyle: 'italic' }}>{f.confidence_reasoning}</div>
      {f.source_documents?.length > 0 && (
        <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {f.source_documents.map((s) => <Pill key={s} text={s.replace(/_/g, ' ')} color="#95a5a6" />)}
        </div>
      )}
    </div>
  )
}

function CitationsTable({ citations }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ textAlign: 'left', borderBottom: '2px solid #e1e4e8' }}>
          <th style={{ padding: 8 }}>Citation</th>
          <th style={{ padding: 8 }}>Exists</th>
          <th style={{ padding: 8 }}>Supports</th>
          <th style={{ padding: 8 }}>Quote</th>
          <th style={{ padding: 8 }}>Conf.</th>
        </tr>
      </thead>
      <tbody>
        {citations.map((c) => (
          <tr key={c.citation_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
            <td style={{ padding: 8 }}>{c.citation_text}</td>
            <td style={{ padding: 8 }}><Pill text={c.exists_verdict.replace(/_/g, ' ')} color={VERDICT_COLOR[c.exists_verdict]} /></td>
            <td style={{ padding: 8 }}><Pill text={c.supports_proposition.replace(/_/g, ' ')} color={VERDICT_COLOR[c.supports_proposition]} /></td>
            <td style={{ padding: 8 }}><Pill text={c.quote_accuracy.replace(/_/g, ' ')} color={VERDICT_COLOR[c.quote_accuracy]} /></td>
            <td style={{ padding: 8 }}>{Math.round(c.confidence * 100)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginTop: 28 }}>
      <h2 style={{ fontSize: 18, borderBottom: '1px solid #e1e4e8', paddingBottom: 6 }}>{title}</h2>
      {children}
    </div>
  )
}

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2 }

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

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: '0 20px', fontFamily: 'system-ui, sans-serif', color: '#2c3e50' }}>
      <h1 style={{ marginBottom: 4 }}>BS Detector</h1>
      <p style={{ color: '#888', marginTop: 0 }}>Legal brief verification pipeline</p>

      <button
        onClick={runAnalysis}
        disabled={loading}
        style={{ padding: '10px 24px', fontSize: 16, cursor: loading ? 'not-allowed' : 'pointer', background: '#2c3e50', color: '#fff', border: 'none', borderRadius: 6 }}
      >
        {loading ? 'Analyzing...' : 'Run Analysis'}
      </button>

      {error && <div style={{ marginTop: 20, color: '#c0392b' }}><strong>Error:</strong> {error}</div>}
      {report === null && !loading && !error && (
        <p style={{ marginTop: 20, color: '#888' }}>Click "Run Analysis" to verify the case documents.</p>
      )}

      {report && (
        <>
          <div style={{ marginTop: 24, color: '#888', fontSize: 14 }}>{report.case}</div>

          {report.errors?.length > 0 && (
            <div style={{ ...card, marginTop: 12, borderLeft: '4px solid #b9770e', background: '#fffaf0' }}>
              <strong>Partial result:</strong> {report.errors.length} agent(s) failed; showing what completed.
              <ul style={{ margin: '6px 0 0', fontSize: 13 }}>{report.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          )}

          {report.judicial_memo && (
            <Section title="Judicial Memo">
              <div style={{ ...card, background: '#f8f9fa', lineHeight: 1.6 }}>{report.judicial_memo}</div>
            </Section>
          )}

          <Section title={`Findings (${findings.length})`}>
            {findings.length === 0
              ? <p style={{ color: '#888' }}>No material verification problems found.</p>
              : findings.map((f) => <FindingCard key={f.id} f={f} />)}
          </Section>

          {report.citations?.length > 0 && (
            <Section title={`Citations (${report.citations.length})`}>
              <CitationsTable citations={report.citations} />
            </Section>
          )}
        </>
      )}
    </div>
  )
}

export default App
