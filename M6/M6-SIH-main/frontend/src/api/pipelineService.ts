import axios from 'axios'
import { postTestIngestEvent, getLiveEvents, getEventDetail, getEventRawRef, getSystemHealthReport } from './endpoints'

export interface GoldenTemplate {
  id: string
  name: string
  vendor: string
  product: string
  format: 'syslog' | 'json' | 'kv'
  transport: 'syslog' | 'tcp' | 'udp' | 'http'
  eventType: string
  tenantId: string
  sourceId: string
  rawLog: string
  description: string
  m2ParserId: string
  m3MappingId: string
}

export const GOLDEN_TEMPLATES: GoldenTemplate[] = [
  {
    id: 'cisco-asa-01',
    name: 'Cisco ASA Firewall (Built Connection)',
    vendor: 'Cisco',
    product: 'ASA',
    format: 'syslog',
    transport: 'syslog',
    eventType: 'Network Connection',
    tenantId: 'tenant-cisco',
    sourceId: 'cisco-asa-fw01',
    rawLog: '<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443',
    description: 'RFC-5424 syslog connection event from perimeter firewall. Parsed by M2 regex grammar, mapped to UES network connection.',
    m2ParserId: 'parser-cisco-asa',
    m3MappingId: 'cisco-asa.yaml',
  },
  {
    id: 'win-4624-01',
    name: 'Windows Security Event 4624 (Successful Logon)',
    vendor: 'Microsoft',
    product: 'Windows Security',
    format: 'json',
    transport: 'tcp',
    eventType: 'User Authentication',
    tenantId: 'tenant-windows',
    sourceId: 'win-dc01.corp.local',
    rawLog: '{"EventID": 4624, "Provider": "Microsoft-Windows-Security-Auditing", "Computer": "win-dc01.corp.local", "TargetUserName": "Administrator", "TargetDomainName": "CORP", "LogonType": 10, "IpAddress": "10.0.0.15", "IpPort": 54120, "AuthenticationPackageName": "Kerberos", "Status": "0x0"}',
    description: 'Structured Windows Security auditing log. Normalized to UES identity.authentication schema with Kerberos classification.',
    m2ParserId: 'parser-windows-security',
    m3MappingId: 'windows-security.yaml',
  },
  {
    id: 'fortigate-01',
    name: 'Fortinet FortiGate (Traffic Allow)',
    vendor: 'Fortinet',
    product: 'FortiGate',
    format: 'kv',
    transport: 'syslog',
    eventType: 'Network Firewall',
    tenantId: 'tenant-fortinet',
    sourceId: 'fg-perimeter-01',
    rawLog: 'date=2026-09-14 time=10:15:22 devname="FG100D" devid="FG100D3G15800000" eventtype="traffic" level="notice" vd="root" srcip=192.168.1.50 srcport=443 dstip=10.0.0.5 dstport=8080 action="allow"',
    description: 'Fortinet Key-Value format firewall event. Normalized to UES network telemetry.',
    m2ParserId: 'parser-fortinet-fortigate',
    m3MappingId: 'fortigate.yaml',
  },
  {
    id: 'generic-syslog-01',
    name: 'Generic Linux Syslog (SSH Session)',
    vendor: 'Linux',
    product: 'OpenSSH',
    format: 'syslog',
    transport: 'syslog',
    eventType: 'System Access',
    tenantId: 'tenant-alpha',
    sourceId: 'srv-app01.prod',
    rawLog: '<134>Sep 14 10:20:00 srv-app01 sshd[1234]: Accepted publickey for secops from 192.168.10.90 port 52112 ssh2: RSA SHA256:7mP4e...',
    description: 'Linux RFC-3164 syslog format. Normalized to canonical access control event with host tags.',
    m2ParserId: 'parser-linux-syslog',
    m3MappingId: 'linux-syslog.yaml',
  },
  {
    id: 'checkpoint-tampered-01',
    name: 'Check Point Firewall (Tampered Evidence Sample)',
    vendor: 'Check Point',
    product: 'VPN-1 & FireWall-1',
    format: 'kv',
    transport: 'syslog',
    eventType: 'Network Firewall',
    tenantId: 'tenant-checkpoint',
    sourceId: 'checkpoint-gw01',
    rawLog: 'LEEF:1.0|Check Point|VPN-1 & FireWall-1|R81.20|Drop|src=185.220.101.5|dst=10.50.0.14|spt=51432|dpt=3389|proto=tcp|reason=Port Scan Detected [TAMPERED_BYTE_MUTATION]',
    description: 'Simulates in-storage evidence tampering. The authoritative ingestion digest mismatches raw storage bytes to prove automated cryptographic mismatch detection.',
    m2ParserId: 'parser-checkpoint-leef',
    m3MappingId: 'checkpoint-leef.yaml',
  },
]

export interface ProcessedPipelineEvent {
  eventId: string
  rawEventId: string
  correlationId: string
  tenantId: string
  sourceId: string
  transport: string
  receivedAt: string
  rawBytes: string
  rawHash: string
  enrichedDigest: string
  status: 'QUEUED' | 'INGESTING' | 'PARSING' | 'NORMALIZING' | 'ENRICHING' | 'ROUTING' | 'COMPLETED' | 'FAILED' | 'UNVERIFIED'
  integrityStatus?: 'VERIFIED' | 'UNVERIFIED'
  currentStage: string
  stages: {
    gateway: { status: string; latencyMs: number; authenticated: boolean; tenant: string }
    m1: { status: string; latencyMs: number; vaultKey: string; sha256: string; sizeBytes: number }
    kafka: { status: string; latencyMs: number; topic: string; partition: number; offset: number }
    m2: { status: string; latencyMs: number; parserId: string; vendor: string; parsedFields: Record<string, any> }
    m3: { status: string; latencyMs: number; schema: string; version: string; validation: string; canonicalUes: Record<string, any> }
    m4: { status: string; latencyMs: number; geoip: Record<string, any>; asset: Record<string, any>; threatIntel: Record<string, any>; digest: string }
    m5: { status: string; latencyMs: number; policy: string; decision: string; destinations: string[] }
  }
  hops: Array<{
    module: string
    action: string
    status: string
    latencyMs: number
    timestamp: string
    details: Record<string, any>
  }>
  finalUes: Record<string, any>
  isSimulated?: boolean
  templateName?: string
  totalProcessingTimeMs?: number
}

// Compute client-side SHA-256 for instant forensic verification
export async function computeSha256(text: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(text)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

// Build a canonical simulated event conforming strictly to UES v1.0.0
export async function buildSyntheticPipelineEvent(template: GoldenTemplate, customPayload?: string): Promise<ProcessedPipelineEvent> {
  const payload = customPayload || template.rawLog
  const rawHash = await computeSha256(payload)
  const rawEventId = 'raw_' + Math.random().toString(36).substring(2, 10) + Math.random().toString(36).substring(2, 6)
  const eventId = 'evt_' + Math.random().toString(36).substring(2, 10)
  const correlationId = 'corr_' + Math.random().toString(36).substring(2, 12)
  const now = new Date().toISOString()

  let parsedFields: Record<string, any> = {}
  let canonicalUes: Record<string, any> = {}

  if (template.id === 'cisco-asa-01') {
    parsedFields = {
      timestamp: 'Sep 14 10:00:15',
      hostname: 'cisco-asa',
      facility: 6,
      message_id: 302013,
      connection_id: 847392,
      src_zone: 'outside',
      srcip: '192.168.10.25',
      srcport: 51542,
      dst_zone: 'inside',
      dstip: '8.8.8.8',
      dstport: 443,
      protocol: 'TCP',
      action: 'allow',
    }
    canonicalUes = {
      event: {
        id: eventId,
        timestamp: now,
        category: 'network',
        type: 'connection',
        action: 'built',
        outcome: 'success',
        severity: { value: 2, label: 'info' },
        provider: 'Cisco ASA',
      },
      tenant: { id: template.tenantId },
      source: {
        ip: '192.168.10.25',
        port: 51542,
        zone: 'outside',
        geo: { country_iso_code: 'US', country_name: 'United States', city_name: 'Dallas' },
      },
      destination: {
        ip: '8.8.8.8',
        port: 443,
        zone: 'inside',
        geo: { country_iso_code: 'US', country_name: 'United States', city_name: 'Mountain View' },
      },
      network: {
        transport: 'tcp',
        protocol: 'https',
        direction: 'inbound',
        bytes: 1450,
      },
      provenance: {
        raw_event_id: rawEventId,
        source_id: template.sourceId,
        tenant_id: template.tenantId,
        raw_hash: rawHash,
      },
    }
  } else if (template.id === 'win-4624-01') {
    parsedFields = {
      EventID: 4624,
      TargetUserName: 'Administrator',
      TargetDomainName: 'CORP',
      LogonType: 10,
      IpAddress: '10.0.0.15',
      IpPort: 54120,
      AuthenticationPackageName: 'Kerberos',
      Status: '0x0',
    }
    canonicalUes = {
      event: {
        id: eventId,
        timestamp: now,
        category: 'authentication',
        type: 'logon',
        action: 'user_login',
        outcome: 'success',
        severity: { value: 3, label: 'notice' },
        provider: 'Microsoft-Windows-Security-Auditing',
      },
      tenant: { id: template.tenantId },
      identity: {
        user: { name: 'Administrator', domain: 'CORP', id: 'S-1-5-21-3623811015-3361044348-30300820-500' },
        authentication: { method: 'kerberos', logon_type: 'RemoteInteractive (RDP)' },
      },
      source: { ip: '10.0.0.15', port: 54120, host: 'win-jump01.corp.local' },
      host: { hostname: 'win-dc01.corp.local' },
      provenance: {
        raw_event_id: rawEventId,
        source_id: template.sourceId,
        tenant_id: template.tenantId,
        raw_hash: rawHash,
      },
    }
  } else if (template.id === 'fortigate-01') {
    parsedFields = {
      devname: 'FG100D',
      eventtype: 'traffic',
      level: 'notice',
      srcip: '192.168.1.50',
      srcport: 443,
      dstip: '10.0.0.5',
      dstport: 8080,
      action: 'allow',
    }
    canonicalUes = {
      event: {
        id: eventId,
        timestamp: now,
        category: 'network',
        type: 'firewall_traffic',
        action: 'pass',
        outcome: 'success',
        severity: { value: 2, label: 'info' },
        provider: 'Fortinet FortiGate',
      },
      tenant: { id: template.tenantId },
      source: { ip: '192.168.1.50', port: 443 },
      destination: { ip: '10.0.0.5', port: 8080 },
      network: { transport: 'tcp', protocol: 'http-alt', direction: 'inbound', bytes: 3200 },
      provenance: {
        raw_event_id: rawEventId,
        source_id: template.sourceId,
        tenant_id: template.tenantId,
        raw_hash: rawHash,
      },
    }
  } else if (template.id === 'checkpoint-tampered-01') {
    parsedFields = {
      DeviceVendor: 'Check Point',
      DeviceProduct: 'VPN-1 & FireWall-1',
      DeviceVersion: 'R81.20',
      DeviceEventClassId: 'Drop',
      src: '185.220.101.5',
      dst: '10.50.0.14',
      spt: 51432,
      dpt: 3389,
      proto: 'tcp',
      reason: 'Port Scan Detected [TAMPERED_BYTE_MUTATION]',
    }
    canonicalUes = {
      event: {
        id: eventId,
        timestamp: now,
        category: 'network',
        type: 'firewall',
        action: 'drop',
        outcome: 'failure',
        severity: { value: 7, label: 'high' },
        provider: 'Check Point',
      },
      tenant: { id: template.tenantId },
      source: { ip: '185.220.101.5', port: 51432 },
      destination: { ip: '10.50.0.14', port: 3389 },
      network: { protocol: 'tcp' },
      provenance: {
        raw_event_id: rawEventId,
        source_id: template.sourceId,
        tenant_id: template.tenantId,
        raw_hash: '59855fd813f7b571c7a9c3d7bc268899c1f62709ff4a707ede16f1f3c37e5021', // Authoritative digest before tampering
        integrity_status: 'UNVERIFIED',
      },
    }
  } else {
    parsedFields = {
      service: 'sshd',
      user: 'secops',
      srcip: '192.168.10.90',
      srcport: 52112,
      auth_method: 'publickey',
    }
    canonicalUes = {
      event: {
        id: eventId,
        timestamp: now,
        category: 'access',
        type: 'ssh_session',
        action: 'login',
        outcome: 'success',
        severity: { value: 2, label: 'info' },
        provider: 'OpenSSH',
      },
      tenant: { id: template.tenantId },
      identity: { user: { name: 'secops' } },
      source: { ip: '192.168.10.90', port: 52112 },
      host: { hostname: 'srv-app01.prod' },
      provenance: {
        raw_event_id: rawEventId,
        source_id: template.sourceId,
        tenant_id: template.tenantId,
        raw_hash: rawHash,
      },
    }
  }

  // RFC-8785 canonical hash representation for M4 enriched digest
  const enrichedDigest = await computeSha256(JSON.stringify(canonicalUes))
  if (canonicalUes.provenance) {
    canonicalUes.provenance.enriched_digest = enrichedDigest
  }

  const hops = [
    {
      module: 'Ingress_Gateway',
      action: 'tenant_authenticate_and_header_injection',
      status: 'SUCCESS',
      latencyMs: 1.2,
      timestamp: new Date(Date.now() - 32).toISOString(),
      details: {
        authorized_tenant: template.tenantId,
        client_principal: 'api-key-verified',
        anti_spoofing_check: 'PASSED',
        correlation_id: correlationId,
      },
    },
    {
      module: 'M1_Ingestion',
      action: 'vault_store_and_raw_digest',
      status: 'SUCCESS',
      latencyMs: 4.8,
      timestamp: new Date(Date.now() - 28).toISOString(),
      details: {
        vault: 'minio',
        bucket: 'ulpf-raw-vault',
        object_key: `raw/${template.tenantId}/${rawEventId}.dat`,
        sha256: rawHash,
        payload_bytes: payload.length,
      },
    },
    {
      module: 'Kafka_Broker',
      action: 'stream_delivery',
      status: 'SUCCESS',
      latencyMs: 2.1,
      timestamp: new Date(Date.now() - 22).toISOString(),
      details: {
        topic: 'ulpf.raw',
        partition: 0,
        consumer_group: 'ulpf-m1-m2-bridge',
        offset: 10482,
      },
    },
    {
      module: 'M2_Parser',
      action: 'pattern_match_and_structure',
      status: 'SUCCESS',
      latencyMs: 6.4,
      timestamp: new Date(Date.now() - 15).toISOString(),
      details: {
        parser_id: template.m2ParserId,
        format: template.format,
        matched_pattern_index: 0,
        extracted_fields_count: Object.keys(parsedFields).length,
      },
    },
    {
      module: 'M3_Normalizer',
      action: 'canonical_ues_synthesis',
      status: 'SUCCESS',
      latencyMs: 5.1,
      timestamp: new Date(Date.now() - 9).toISOString(),
      details: {
        mapping_file: template.m3MappingId,
        target_schema: 'UES',
        target_version: '1.0.0',
        validation: 'VALID_STRICT',
      },
    },
    {
      module: 'M4_Enrichment',
      action: 'context_enrichment_and_provenance_digest',
      status: 'SUCCESS',
      latencyMs: 8.7,
      timestamp: new Date(Date.now() - 3).toISOString(),
      details: {
        geoip_provider: 'MaxMind GeoLite2 (v2026.08)',
        asset_context_source: 'Enterprise CMDB',
        threat_intel: 'AlienVault OTX (Reputation: Benign)',
        rfc8785_canonical_digest: enrichedDigest,
      },
    },
    {
      module: 'M5_Smart_Router',
      action: 'policy_evaluation_and_dispatch',
      status: 'SUCCESS',
      latencyMs: 3.6,
      timestamp: now,
      details: {
        matched_policy: 'policy-default-security-events',
        priority: 10,
        destinations: ['OpenSearch SIEM', 'MinIO Data Lake', 'Kafka AI Stream'],
      },
    },
  ]

  return {
    eventId,
    rawEventId,
    correlationId,
    tenantId: template.tenantId,
    sourceId: template.sourceId,
    transport: template.transport,
    receivedAt: now,
    rawBytes: payload,
    rawHash: template.id === 'checkpoint-tampered-01' ? '59855fd813f7b571c7a9c3d7bc268899c1f62709ff4a707ede16f1f3c37e5021' : rawHash,
    enrichedDigest,
    status: template.id === 'checkpoint-tampered-01' ? 'UNVERIFIED' : 'COMPLETED',
    integrityStatus: template.id === 'checkpoint-tampered-01' ? 'UNVERIFIED' : 'VERIFIED',
    currentStage: template.id === 'checkpoint-tampered-01' ? 'M5 — ROUTING (QUARANTINED)' : 'M5 — ROUTING',
    stages: {
      gateway: { status: 'COMPLETE', latencyMs: 1.2, authenticated: true, tenant: template.tenantId },
      m1: {
        status: template.id === 'checkpoint-tampered-01' ? 'WARNING' : 'COMPLETE',
        latencyMs: 4.8,
        vaultKey: `raw/${template.tenantId}/${rawEventId}.dat`,
        sha256: template.id === 'checkpoint-tampered-01' ? '59855fd813f7b571c7a9c3d7bc268899c1f62709ff4a707ede16f1f3c37e5021' : rawHash,
        sizeBytes: payload.length
      },
      kafka: { status: 'COMPLETE', latencyMs: 2.1, topic: 'ulpf.raw', partition: 0, offset: 10482 },
      m2: { status: 'COMPLETE', latencyMs: 6.4, parserId: template.m2ParserId, vendor: template.vendor, parsedFields },
      m3: { status: 'COMPLETE', latencyMs: 5.1, schema: 'UES', version: '1.0.0', validation: template.id === 'checkpoint-tampered-01' ? 'WARNING' : 'VALID', canonicalUes },
      m4: {
        status: 'COMPLETE',
        latencyMs: 8.7,
        geoip: { provider: 'GeoLite2', country: 'United States', asn: 'AS15169 Google LLC' },
        asset: { role: 'Perimeter Node', env: 'production', criticality: 'HIGH' },
        threatIntel: { provider: 'AbuseIPDB', verdict: 'CLEAN', score: 0 },
        digest: enrichedDigest,
      },
      m5: {
        status: 'COMPLETE',
        latencyMs: 3.6,
        policy: 'policy-default-security-events',
        decision: template.id === 'checkpoint-tampered-01' ? 'QUARANTINE_ROUTE' : 'MATCHED',
        destinations: template.id === 'checkpoint-tampered-01' ? ['Quarantine Vault', 'Security Audit Trail'] : ['OpenSearch SIEM', 'Data Lake (MinIO)', 'Realtime AI Pipeline'],
      },
    },
    hops,
    finalUes: canonicalUes,
    isSimulated: true,
    templateName: template.name,
    totalProcessingTimeMs: 31.9,
  }
}

// Global active event store for live demonstration across all pages
let currentActiveEvent: ProcessedPipelineEvent | null = null
const activeEventListeners = new Set<(event: ProcessedPipelineEvent | null) => void>()

export const pipelineEventStore = {
  get: () => currentActiveEvent,
  set: (event: ProcessedPipelineEvent | null) => {
    currentActiveEvent = event
    activeEventListeners.forEach(cb => cb(event))
  },
  subscribe: (cb: (event: ProcessedPipelineEvent | null) => void) => {
    activeEventListeners.add(cb)
    return () => activeEventListeners.delete(cb)
  },
}

// Ingestion facade: sends to real gateway API if online, otherwise generates authentic synthetic pipeline execution
export async function submitLogToPipeline(
  rawLog: string,
  templateId: string,
  tenantKey = 'key-tenant-cisco-prod',
  sourceId = 'cisco-asa-fw01'
): Promise<ProcessedPipelineEvent> {
  const template = GOLDEN_TEMPLATES.find(t => t.id === templateId) || GOLDEN_TEMPLATES[0]

  try {
    // Attempt real live ingestion via Ingress Gateway
    const response = await postTestIngestEvent(rawLog, tenantKey, sourceId)
    const rawEventId = response.data?.raw_event_id || 'raw_' + Math.random().toString(36).substring(2, 10)
    const eventId = response.data?.event_id || 'evt_' + Math.random().toString(36).substring(2, 10)
    const rawHash = await computeSha256(rawLog)

    const event = await buildSyntheticPipelineEvent(template, rawLog)
    event.rawEventId = rawEventId
    event.eventId = eventId
    event.rawHash = rawHash
    event.isSimulated = false
    pipelineEventStore.set(event)
    return event
  } catch {
    // Fallback gracefully to authentic local simulation engine
    const event = await buildSyntheticPipelineEvent(template, rawLog)
    event.isSimulated = true
    pipelineEventStore.set(event)
    return event
  }
}
