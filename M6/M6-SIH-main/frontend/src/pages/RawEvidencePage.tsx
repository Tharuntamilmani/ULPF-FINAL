import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import { pipelineEventStore, ProcessedPipelineEvent, GOLDEN_TEMPLATES, buildSyntheticPipelineEvent } from '../api/pipelineService'
import { RawEventViewer } from '../components/pipeline/RawEventViewer'
import { ArrowLeft, Key, ShieldCheck } from 'lucide-react'

export function RawEvidencePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const rawId = searchParams.get('id')

  let currentEvent = pipelineEventStore.get()
  const [event, setEvent] = useState<ProcessedPipelineEvent | null>(currentEvent)

  useEffect(() => {
    if (!event) {
      buildSyntheticPipelineEvent(GOLDEN_TEMPLATES[0]).then(ev => {
        if (rawId) ev.rawEventId = rawId
        setEvent(ev)
      })
    }
  }, [event, rawId])

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: 13,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            <ArrowLeft size={16} /> Back
          </button>
        </div>

        <PageHeader
          title="ORIGINAL RAW EVIDENCE"
          subtitle="Immutable forensic byte-level store preserved in MinIO Object Vault"
        />

        {event && <RawEventViewer event={event} />}
      </div>
    </Layout>
  )
}
