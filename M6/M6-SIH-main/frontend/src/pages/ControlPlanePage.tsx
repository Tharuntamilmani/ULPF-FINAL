import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Card } from '../components/ui/Card'
import {
  Building2,
  Server,
  Code2,
  GitMerge,
  Shield,
  History,
  ClipboardList,
  Sparkles,
  Layers,
  ArrowRight,
  Share2,
  CheckCircle2,
} from 'lucide-react'

export function ControlPlanePage() {
  const navigate = useNavigate()

  const controlCards = [
    {
      title: 'TENANTS',
      subtitle: 'Multi-Tenant Governance',
      description: 'Cryptographic API keys, per-tenant resource limits, isolated data lakes, and security perimeter policies.',
      count: '4 Active',
      path: '/tenants',
      icon: Building2,
      color: 'var(--accent)',
    },
    {
      title: 'SOURCES',
      subtitle: 'Sensors & Collectors',
      description: 'Syslog listeners (TCP/UDP), HTTP webhooks, Windows agent endpoints, and zone routing definitions.',
      count: '12 Registered',
      path: '/sources',
      icon: Server,
      color: 'var(--cyan)',
    },
    {
      title: 'PARSERS',
      subtitle: 'Vendor Grammar Registry',
      description: 'Vendor parsers (Cisco, Microsoft, Fortinet, Linux) with ReDoS safety analysis, grok expressions, and live lifecycle state.',
      count: '6 Active',
      path: '/parsers',
      icon: Code2,
      color: 'var(--purple)',
    },
    {
      title: 'MAPPINGS',
      subtitle: 'UES Normalization Mappings',
      description: 'Field translation matrices converting vendor fields into canonical Universal Event Schema v1.0.0 taxonomies.',
      count: '8 Rulesets',
      path: '/mappings',
      icon: GitMerge,
      color: 'var(--green)',
    },
    {
      title: 'ENRICHMENT',
      subtitle: 'Context & Threat Intel',
      description: 'MaxMind GeoIP, AlienVault OTX Threat Intelligence, and Enterprise CMDB asset context providers.',
      count: '3 Providers',
      path: '/configuration',
      icon: Sparkles,
      color: '#ec4899',
    },
    {
      title: 'POLICIES',
      subtitle: 'M5 Routing Rules',
      description: 'Smart Router dispatch matrices for OpenSearch SIEM, compliance data lakes, and real-time AI anomaly detection pipelines.',
      count: '5 Evaluated',
      path: '/policies',
      icon: Shield,
      color: 'var(--yellow)',
    },
    {
      title: 'VERSIONS',
      subtitle: 'Configuration Snapshots',
      description: 'Immutable version control for all parsers and policies with atomic distribution and zero-downtime rollback.',
      count: 'v1.2.0 Active',
      path: '/configuration',
      icon: History,
      color: 'var(--accent)',
    },
    {
      title: 'AUDIT',
      subtitle: 'Administrative Provenance',
      description: 'Cryptographically sealed audit trail logging every configuration update, deployment ACK, and administrative operation.',
      count: '1,420 Entries',
      path: '/audit',
      icon: ClipboardList,
      color: '#14b8a6',
    },
  ]

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <PageHeader
          title="ULPF CONTROL PLANE"
          subtitle="Central governance, schema orchestration, and configuration distribution across the M1–M5 data plane"
        />

        {/* Core Architecture Distinction Banner */}
        <div
          style={{
            background: 'radial-gradient(ellipse at top, #1c1836 0%, #11101e 100%)',
            border: '1px solid rgba(139, 92, 246, 0.4)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#c4b5fd', fontWeight: 800, fontSize: 12 }}>
              <Layers size={18} />
              ARCHITECTURE SEPARATION PRINCIPLE
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 900, color: '#ffffff', marginTop: 4 }}>
              M6 Control Plane vs. M1–M5 Data Plane
            </h2>
            <p style={{ fontSize: 13, color: '#d8b4fe', marginTop: 6, maxWidth: 680, lineHeight: 1.5 }}>
              <strong>M1–M5 (Data Plane):</strong> Autonomous, high-throughput microservices processing raw wire logs into normalized UES events in memory and streaming through Kafka.<br />
              <strong>M6 (Control Plane):</strong> Governs tenant policies, hot-reloads parsers, enforces schemas, and distributes configuration snapshots with zero processing interruption.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, textAlign: 'right' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid var(--green)', borderRadius: 6, color: 'var(--green)', fontSize: 12, fontWeight: 800 }}>
              <CheckCircle2 size={14} />
              DATA PLANE SYNC: 100% ACKED
            </div>
            <div style={{ fontSize: 11, color: '#a78bfa' }}>
              Port :18086 • Transactional Outbox Active
            </div>
          </div>
        </div>

        {/* 8 Control Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {controlCards.map(card => {
            const Icon = card.icon
            return (
              <div
                key={card.title}
                onClick={() => navigate(card.path)}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  minHeight: 180,
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: 'var(--bg-elevated)',
                        border: `1px solid ${card.color}`,
                        color: card.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Icon size={18} />
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 700, color: card.color, background: 'var(--bg-surface)', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border)' }}>
                      {card.count}
                    </span>
                  </div>

                  <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary)' }}>
                    {card.title}
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: card.color, marginTop: 2 }}>
                    {card.subtitle}
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.4 }}>
                    {card.description}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--accent)', fontSize: 12, fontWeight: 700, marginTop: 14 }}>
                  Manage {card.title} <ArrowRight size={14} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </Layout>
  )
}
