import React from 'react'
import { X, CheckCircle2, Shield, Database, Cpu, Layers, ExternalLink, Key, Share2, Server } from 'lucide-react'
import { ProcessedPipelineEvent } from '../../api/pipelineService'

interface StageDetailDrawerProps {
  nodeId: string | null
  event: ProcessedPipelineEvent | null
  onClose: () => void
  onViewRaw?: () => void
}

export function StageDetailDrawer({ nodeId, event, onClose, onViewRaw }: StageDetailDrawerProps) {
  if (!nodeId) return null

  const renderContent = () => {
    switch (nodeId) {
      case 'raw':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>
                RAW WIRE LOG INGRESS
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Unparsed Security Wire Telemetry
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Untrusted external telemetry received over Syslog (RFC-5424 / RFC-3164), HTTP REST endpoints, or raw TCP sockets prior to perimeter authentication and envelope processing.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>SOURCE SENSOR</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>
                  {event?.sourceId || 'cisco-asa-fw01'}
                </div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>INGRESS TRANSPORT</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>
                  {(event?.transport || 'syslog').toUpperCase()}
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                RAW WIRE PAYLOAD (PRE-INGESTION)
              </div>
              <pre className="code-block" style={{ margin: 0, fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
{event?.rawBytes || '<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443'}
              </pre>
            </div>
          </div>
        )

      case 'gateway':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>
                INGRESS SECURITY PERIMETER
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Boundary Authentication & Tenant Isolation
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Intercepts external client traffic at port :18080. Validates tenant API keys, strips client-supplied unverified headers, prevents tenant spoofing, and injects trusted correlation context.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>AUTH STATUS</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>✓ PASSED (Bearer Token)</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>ANTI-SPOOFING CHECK</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>✓ BOUND TENANT VERIFIED</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                INJECTED SYSTEM HEADERS (FORWARDED TO M1)
              </div>
              <pre className="code-block" style={{ margin: 0, fontSize: 11 }}>
{`X-Tenant-ID: ${event?.tenantId || 'tenant-cisco'}
X-Source-ID: ${event?.sourceId || 'cisco-asa-fw01'}
X-Correlation-ID: ${event?.correlationId || 'corr_98234-a1e9'}
X-Authenticated-Principal: verified-client-agent
Authorization: Bearer sec-m1-token-sysadmin-9901`}
              </pre>
            </div>
          </div>
        )

      case 'm1':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--green)', textTransform: 'uppercase' }}>
                M1 — INGESTION & RAW EVIDENCE VAULT
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Authoritative Digest & Immutable Storage
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Receives wire logs, generates the immutable <strong style={{ color: '#fff' }}>raw_event_id</strong>, computes the authoritative SHA-256 digest directly over inbound bytes, stores original bytes in MinIO, and publishes envelope to Kafka.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>RAW EVENT ID</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--cyan)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                  {event?.rawEventId || 'raw_cisco_asa_847392'}
                </div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>PAYLOAD SIZE</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>
                  {event?.rawBytes?.length || 136} bytes
                </div>
              </div>
            </div>

            <div style={{ background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--cyan)', marginBottom: 4 }}>
                AUTHORITATIVE RAW SHA-256 (UNMUTATED EVIDENCE)
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#f8fafc', wordBreak: 'break-all' }}>
                {event?.rawHash || 'c8307d722c83ef873491ae9320f...'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 4 }}>MINIO VAULT OBJECT STORAGE REF</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-surface)', padding: '8px 10px', borderRadius: 4, border: '1px solid var(--border)' }}>
                {event?.stages.m1.vaultKey || `raw/tenant-cisco/${event?.rawEventId || 'raw_cisco'}.dat`}
              </div>
            </div>

            {onViewRaw && (
              <button
                onClick={onViewRaw}
                style={{
                  padding: '10px 14px',
                  background: 'var(--cyan)',
                  border: 'none',
                  borderRadius: 6,
                  color: '#000',
                  fontWeight: 700,
                  fontSize: 12,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                }}
              >
                <Key size={14} /> VIEW ORIGINAL RAW EVIDENCE
              </button>
            )}
          </div>
        )

      case 'kafka':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--yellow)', textTransform: 'uppercase' }}>
                KAFKA STREAMING INFRASTRUCTURE
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Decoupled Durable Broker & Bridge Consumer
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Provides durable buffering between high-throughput M1 ingestion and M2 parsing. The <strong style={{ color: '#fff' }}>ulpf-m1-m2-bridge</strong> consumer guarantees at-least-once delivery with automatic retry policies and offset commits.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>TOPIC</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>ulpf.raw</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>CONSUMER GROUP</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>ulpf-m1-m2-bridge</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                BROKER PARAMETERS
              </div>
              <pre className="code-block" style={{ margin: 0, fontSize: 11 }}>
{`Bootstrap Servers: localhost:9092
Partition: 0 (Keyed by tenant_id)
Offset Commit Mode: Synchronous post-M2 200 OK
Dead-Letter Topic: ulpf.dlq (Transient backoff 3x)`}
              </pre>
            </div>
          </div>
        )

      case 'm2':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>
                M2 — VENDOR PARSING ENGINE
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Grammar Matching & Structured Field Extraction
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Applies tenant-scoped parser definitions (Regex, Grok, Key-Value) with ReDoS safety limits to parse vendor-specific wire formats into intermediate <strong style={{ color: '#fff' }}>ParsedEvent</strong> objects.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>ACTIVE PARSER</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', marginTop: 2 }}>
                  {event?.stages.m2.parserId || 'parser-cisco-asa'}
                </div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>PARSER STATUS</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>PARSED (200 OK)</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                EXTRACTED PARSED FIELDS (ParsedEvent)
              </div>
              <pre className="code-block" style={{ margin: 0, fontSize: 11, maxHeight: 180 }}>
                {JSON.stringify(event?.stages.m2.parsedFields || {}, null, 2)}
              </pre>
            </div>
          </div>
        )

      case 'm3':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--green)', textTransform: 'uppercase' }}>
                M3 — UES CANONICAL NORMALIZER
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Universal Event Schema v1.0.0 Synthesis
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Maps disparate vendor classifications into standard <strong style={{ color: '#fff' }}>Universal Event Schema (UES)</strong> entities: source, destination, network, identity, and action taxonomies.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>SCHEMA</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', marginTop: 2 }}>Canonical UES</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>VERSION</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>v1.0.0</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>VALIDATION</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>✓ STRICT VALID</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                CANONICAL UES STRUCTURE (PREVIEW)
              </div>
              <pre className="code-block" style={{ margin: 0, fontSize: 11, maxHeight: 180 }}>
                {JSON.stringify(event?.stages.m3.canonicalUes || {}, null, 2)}
              </pre>
            </div>
          </div>
        )

      case 'm4':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase' }}>
                M4 — SECURITY ENRICHMENT & PROVENANCE
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Context Intelligence & RFC-8785 Digest
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Enriches the event with GeoIP, CMDB asset context, and threat intelligence while preserving provenance and calculating the post-enrichment digest.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>GEOIP</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>MaxMind GeoLite2</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>ASSET CONTEXT</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', marginTop: 2 }}>Enterprise CMDB</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>THREAT INTEL</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>OTX (Benign)</div>
              </div>
            </div>

            <div style={{ background: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#c4b5fd', marginBottom: 4 }}>
                RFC-8785 CANONICAL ENRICHED DIGEST (M4)
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#f5f3ff', wordBreak: 'break-all' }}>
                {event?.enrichedDigest || 'f9018247ca881e...'}
              </div>
            </div>
          </div>
        )

      case 'm5':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase' }}>
                M5 — SMART POLICY ROUTER
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginTop: 4 }}>
                Policy Evaluation & Multiplexed Delivery
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Evaluates tenant routing policies against canonical event fields. Routes events concurrently to OpenSearch SIEM, raw data lake, and realtime AI analytics pipelines.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>POLICY DECISION</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>✓ MATCHED</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>EVALUATION POLICY</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', marginTop: 2 }}>policy-security-alerts</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                ROUTED DESTINATIONS
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>OpenSearch SIEM (:9200)</span>
                  <span style={{ color: 'var(--green)', fontSize: 11, fontWeight: 700 }}>✓ INDEXED</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Cold Storage Lake (MinIO)</span>
                  <span style={{ color: 'var(--green)', fontSize: 11, fontWeight: 700 }}>✓ STORED</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>AI Anomaly Stream</span>
                  <span style={{ color: 'var(--green)', fontSize: 11, fontWeight: 700 }}>✓ DISPATCHED</span>
                </div>
              </div>
            </div>
          </div>
        )

      case 'm6':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '12px', background: '#19172e', border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#c4b5fd', textTransform: 'uppercase' }}>
                M6 — CONTROL PLANE GOVERNANCE
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#f5f3ff', marginTop: 4 }}>
                Centralized Configuration & Versioned Distribution
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                Provides zero-downtime hot-reloading for parsers, UES schema mappings, and routing policies across the entire data plane via a transactional outbox and worker synchronization.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>CONTROL PLANE STATUS</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--green)', marginTop: 2 }}>● OPERATIONAL (:18086)</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: 10, borderRadius: 6, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>CONFIG SNAPSHOT</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#c4b5fd', marginTop: 2 }}>v1.2.0 (Synchronized)</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>
                CONFIGURATION DISTRIBUTION LIFECYCLE
              </div>
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6, padding: '12px', fontSize: 11, lineHeight: 1.6 }}>
                M6 Outbox → Validation → Version Stamp → Atomic Materialization → Module ACK → Active
              </div>
            </div>
          </div>
        )

      default:
        return (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Click on any module node in the live pipeline to inspect its contract, cryptographic proofs, and processing role.
          </div>
        )
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.4)',
        zIndex: 1050,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          background: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border)',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-4px 0 20px rgba(0,0,0,0.08)',
          overflowY: 'auto',
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-elevated)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase' }}>
              MODULE INSPECTION: {nodeId.toUpperCase()}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              padding: 4,
              borderRadius: 4,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Drawer Body */}
        <div style={{ padding: 20, flex: 1 }}>
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
