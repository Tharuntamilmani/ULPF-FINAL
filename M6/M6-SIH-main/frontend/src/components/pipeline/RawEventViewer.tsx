import React, { useState } from 'react'
import { ProcessedPipelineEvent, computeSha256 } from '../../api/pipelineService'
import { Copy, Check, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'

interface RawEventViewerProps {
  event?: ProcessedPipelineEvent
  rawBytes?: string
  sha256Hash?: string
  rawEventId?: string
  storageRef?: string
}

export function RawEventViewer({
  event,
  rawBytes: propRawBytes,
  sha256Hash: propSha256,
  rawEventId: propRawId,
  storageRef: propStorageRef,
}: RawEventViewerProps) {
  const [copied, setCopied] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verifiedHash, setVerifiedHash] = useState<string | null>(null)
  const [isMatch, setIsMatch] = useState<boolean | null>(null)

  const rawBytes = event?.rawBytes ?? propRawBytes ?? ''
  const sha256Hash = event?.rawHash ?? propSha256 ?? ''
  const rawEventId = event?.rawEventId ?? propRawId ?? 'unknown'
  const storageRef = propStorageRef ?? `s3://ulpf-raw-vault/raw/${event?.tenantId ?? 'default'}/${rawEventId}.dat`

  const handleCopy = () => {
    navigator.clipboard.writeText(rawBytes)
    setCopied(true)
    toast.success('Raw event copied')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleVerifyIntegrity = async () => {
    setVerifying(true)
    try {
      const computed = await computeSha256(rawBytes)
      setVerifiedHash(computed)
      const cleanExpected = sha256Hash.replace(/^sha256:/i, '').trim().toLowerCase()
      const match = computed.toLowerCase() === cleanExpected
      setIsMatch(match)
      if (match) {
        toast.success('SHA-256 Match: 100% Raw Evidence Integrity Verified')
      } else {
        toast.error('Cryptographic hash mismatch! Evidence payload does not match Ingestion seal.')
      }
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '12px 14px',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 8,
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
            RAW EVIDENCE LOG VIEWER
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {storageRef} • {rawBytes.length} bytes
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={handleCopy}
            className="btn btn-secondary"
          >
            {copied ? <Check size={12} color="var(--green)" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={handleVerifyIntegrity}
            disabled={verifying}
            className="btn btn-primary"
          >
            <ShieldCheck size={12} />
            <span>{verifying ? 'Computing...' : 'Verify Hash'}</span>
          </button>
        </div>
      </div>

      {/* Hash Verification Strip */}
      <div
        style={{
          padding: '6px 10px',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius)',
          fontSize: 11.5,
          display: 'flex',
          flexDirection: 'column',
          gap: 3,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ color: 'var(--text-secondary)' }}>M1 Ingestion SHA-256: </span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{sha256Hash}</span>
          </div>

          {isMatch !== null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className={`status-dot ${isMatch ? 'green' : 'red'}`} />
              <span style={{ fontWeight: 700, color: isMatch ? 'var(--green)' : 'var(--red)', fontSize: 11 }}>
                {isMatch ? 'HASH VERIFIED (100% MATCH)' : 'UNVERIFIED (HASH MISMATCH DETECTED)'}
              </span>
            </div>
          )}
        </div>

        {verifiedHash && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 }}>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Client Recomputed SHA-256: </span>
              <span style={{ fontFamily: 'var(--font-mono)', color: isMatch ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                {verifiedHash}
              </span>
            </div>
            {!isMatch && (
              <span style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--red)', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', padding: '1px 6px', borderRadius: 4 }}>
                TAMPERED / CORRUPT
              </span>
            )}
          </div>
        )}
      </div>

      {/* Raw Payload Monospace */}
      <div>
        <pre className="code-editor" style={{ minHeight: 180, maxHeight: 400 }}>
          {rawBytes}
        </pre>
      </div>
    </div>
  )
}
