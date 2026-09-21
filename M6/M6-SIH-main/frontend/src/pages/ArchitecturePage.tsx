import React from 'react'
import { Layout, PageHeader } from '../components/layout/Layout'
import { ArrowRight, ArrowDown, Database, Cpu, Shield, Layers, Share2, Server, Key, Radio } from 'lucide-react'

export function ArchitecturePage() {
  const dataPlaneComponents = [
    { name: 'SOURCES', desc: 'Syslog (RFC-5424/3164), TCP, UDP, Windows Agent, HTTP', port: '18514 / 18515', color: '#94a3b8' },
    { name: 'GATEWAY', desc: 'Tenant authentication, anti-spoofing header injection, perimeter isolation', port: '18080', color: 'var(--accent)' },
    { name: 'M1 INGESTION', desc: 'Raw evidence MinIO vault storage, authoritative SHA-256 byte digest calculation', port: '18001', color: 'var(--cyan)' },
    { name: 'KAFKA STREAM', desc: 'Durable topic ulpf.raw, consumer group ulpf-m1-m2-bridge', port: '9092', color: 'var(--yellow)' },
    { name: 'M2 PARSER', desc: 'Vendor grok/regex parsing, ReDoS protection, ParsedEvent structure', port: '18082', color: 'var(--accent)' },
    { name: 'M3 NORMALIZER', desc: 'Canonical Universal Event Schema (UES v1.0.0) field mapping', port: '18083', color: 'var(--green)' },
    { name: 'M4 ENRICHMENT', desc: 'GeoIP, CMDB asset context, Threat Intel & RFC-8785 canonical hash', port: '18004', color: '#c084fc' },
    { name: 'M5 SMART ROUTER', desc: 'Rule engine policy evaluation, conditional routing & dispatch', port: '18085', color: 'var(--accent)' },
    { name: 'OUTPUTS', desc: 'OpenSearch SIEM (:9200), Cold Storage Lake (MinIO), Realtime AI Stream', port: 'Cluster', color: 'var(--green)' },
  ]

  const infraComponents = [
    { name: 'PostgreSQL', port: '5432', role: 'M6 Relational Metadata & Audit Log Store' },
    { name: 'Redis', port: '6379', role: 'Idempotency Cache & Token Rate Limiter' },
    { name: 'Apache Kafka', port: '9092', role: 'Distributed Streaming Log Backbone' },
    { name: 'MinIO (S3)', port: '9000', role: 'Immutable Raw Evidence Vault & Data Lake' },
    { name: 'OpenSearch', port: '9200', role: 'SIEM Analytics & Search Engine Index' },
  ]

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <PageHeader
          title="SYSTEM ARCHITECTURE"
          subtitle="Comprehensive ULPF architectural topology designed for high-scale SOC presentation"
        />

        {/* SECTION 1: CONTROL PLANE TIER */}
        <div style={{ background: '#18152e', border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Layers size={18} color="#c4b5fd" />
              <h3 style={{ fontSize: 16, fontWeight: 800, color: '#f5f3ff' }}>
                CONTROL PLANE (M6 GOVERNANCE TIER)
              </h3>
            </div>
            <span style={{ fontSize: 11, color: '#c4b5fd', background: 'rgba(139, 92, 246, 0.2)', padding: '3px 10px', borderRadius: 4, fontWeight: 700 }}>
              PORT :18086 • CONFIG SYNC WORKER :18081
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: 20, alignItems: 'center' }}>
            <div style={{ background: 'var(--bg-surface)', padding: 16, borderRadius: 8, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>M6 Control Plane API</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Central manager for Tenants, Parsers, UES Mappings, Policies, and Audits. Writes outbox events to distribute zero-downtime hot reloads.
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 6 }}>
                ConfigurationSync <Share2 size={14} />
              </div>
              <div style={{ flex: 1, height: 2, background: 'rgba(139, 92, 246, 0.4)' }} />
              <div style={{ fontSize: 11, color: '#c4b5fd', background: 'var(--bg-surface)', padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border)' }}>
                Atomic materialization & Compliant ACK across M1, M2, M3, M4, M5
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 2: DATA PLANE FLOW */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <Cpu size={18} color="var(--accent)" />
            <h3 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)' }}>
              DATA PLANE (PIPELINE EXECUTION TIER)
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
            {dataPlaneComponents.map((comp, idx) => (
              <div
                key={comp.name}
                style={{
                  background: 'var(--bg-surface)',
                  border: `1px solid var(--border)`,
                  borderTop: `3px solid ${comp.color}`,
                  borderRadius: 8,
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  minHeight: 130,
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)' }}>
                      {comp.name}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      :{comp.port}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.4 }}>
                    {comp.desc}
                  </p>
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: comp.color, marginTop: 10 }}>
                  Stage {idx + 1} of 9
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION 3: INFRASTRUCTURE DATASTORES */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <Database size={18} color="var(--green)" />
            <h3 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)' }}>
              INFRASTRUCTURE BACKBONE DATASTORES
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            {infraComponents.map(infra => (
              <div
                key={infra.name}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: 14,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{infra.name}</span>
                  <span style={{ fontSize: 10, color: 'var(--green)', fontFamily: 'var(--font-mono)' }}>:{infra.port}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.3 }}>
                  {infra.role}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  )
}
