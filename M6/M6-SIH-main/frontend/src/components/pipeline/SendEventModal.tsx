import React, { useState } from 'react'
import { X, Send, ShieldAlert, CheckCircle2 } from 'lucide-react'
import { GOLDEN_TEMPLATES } from '../../api/pipelineService'

interface SendEventModalProps {
  isOpen: boolean
  onClose: () => void
  onSend: (rawLog: string, templateId: string, tenantId: string, sourceId: string) => Promise<void>
  isSending: boolean
}

export function SendEventModal({ isOpen, onClose, onSend, isSending }: SendEventModalProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('cisco-asa-01')
  const activeTemplate = GOLDEN_TEMPLATES.find(t => t.id === selectedTemplateId) || GOLDEN_TEMPLATES[0]

  const [rawLog, setRawLog] = useState<string>(activeTemplate.rawLog)
  const [tenantId, setTenantId] = useState<string>(activeTemplate.tenantId)
  const [sourceId, setSourceId] = useState<string>(activeTemplate.sourceId)

  if (!isOpen) return null

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplateId(templateId)
    const t = GOLDEN_TEMPLATES.find(tpl => tpl.id === templateId)
    if (t) {
      setRawLog(t.rawLog)
      setTenantId(t.tenantId)
      setSourceId(t.sourceId)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSend(rawLog, selectedTemplateId, tenantId, sourceId)
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 20,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 620,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-elevated)',
          }}
        >
          <div>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
              SEND TEST LOG EVENT
            </h3>
            <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 1 }}>
              Dispatch authentic vendor telemetry through Ingress Security Gateway (:18080)
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost"
            style={{ padding: 4 }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Preset Selector */}
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
              SELECT LOG TEMPLATE
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
              {GOLDEN_TEMPLATES.map(tpl => {
                const isSelected = tpl.id === selectedTemplateId
                return (
                  <div
                    key={tpl.id}
                    onClick={() => handleTemplateChange(tpl.id)}
                    style={{
                      padding: '8px 10px',
                      background: isSelected ? 'var(--accent-subtle)' : 'var(--bg-elevated)',
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                      borderRadius: 'var(--radius)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                      transition: 'border-color 0.1s ease',
                    }}
                  >
                    <div style={{ marginTop: 2 }}>
                      {isSelected ? (
                        <CheckCircle2 size={13} color="var(--accent)" />
                      ) : (
                        <div style={{ width: 13, height: 13, borderRadius: '50%', border: '1px solid var(--border)' }} />
                      )}
                    </div>
                    <div>
                      <div style={{ fontSize: 11.5, fontWeight: 600, color: isSelected ? 'var(--accent)' : 'var(--text-primary)' }}>
                        {tpl.name}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 1 }}>
                        {tpl.vendor} • {tpl.transport.toUpperCase()} • {tpl.eventType}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Tenant & Source Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                TARGET TENANT
              </label>
              <input
                type="text"
                value={tenantId}
                onChange={e => setTenantId(e.target.value)}
                style={{ width: '100%', fontFamily: 'var(--font-mono)' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                SOURCE SENSOR ID
              </label>
              <input
                type="text"
                value={sourceId}
                onChange={e => setSourceId(e.target.value)}
                style={{ width: '100%', fontFamily: 'var(--font-mono)' }}
                required
              />
            </div>
          </div>

          {/* Raw Log Payload */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                RAW LOG PAYLOAD (ASCII BYTES)
              </label>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {rawLog.length} bytes
              </span>
            </div>
            <textarea
              rows={4}
              value={rawLog}
              onChange={e => setRawLog(e.target.value)}
              className="code-editor"
              style={{ width: '100%', resize: 'vertical' }}
            />
          </div>

          {/* Security Notice */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 10px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius)',
              fontSize: 11,
              color: 'var(--text-secondary)',
            }}
          >
            <ShieldAlert size={13} color="var(--accent)" />
            <span>
              Ingress Gateway verifies Bearer authentication and cryptographically seals tenant boundaries before M1 vault storage.
            </span>
          </div>

          {/* Footer Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSending || !rawLog.trim()}
              className="btn btn-primary"
            >
              <Send size={11} />
              <span>{isSending ? 'Transiting Pipeline...' : 'Dispatch Event'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
