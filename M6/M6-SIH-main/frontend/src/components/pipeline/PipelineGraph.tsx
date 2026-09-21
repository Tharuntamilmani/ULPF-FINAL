import React from 'react'
import { PipelineNode } from './PipelineNode'
import { PipelineConnector } from './PipelineConnector'
import { ProcessedPipelineEvent } from '../../api/pipelineService'

export const PIPELINE_STAGES = [
  'raw',
  'gateway',
  'm1',
  'kafka',
  'm2',
  'm3',
  'm4',
  'm5',
  'destinations',
] as const

export type PipelineStageKey = (typeof PIPELINE_STAGES)[number]

interface PipelineGraphProps {
  activeEvent: ProcessedPipelineEvent | null
  selectedNodeId: string | null
  onSelectNode: (nodeId: string) => void
  animatingStage: string | null
  stageDurationMs?: number
}

export function PipelineGraph({
  activeEvent,
  selectedNodeId,
  onSelectNode,
  animatingStage,
  stageDurationMs = 550,
}: PipelineGraphProps) {
  const getNodeStatus = (nodeId: string): 'active' | 'healthy' => {
    return animatingStage === nodeId ? 'active' : 'healthy'
  }

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '12px 14px',
        overflowX: 'auto',
      }}
    >
      {/* 9-Stage Technical Data Plane Pipeline */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 0,
          minWidth: 1180,
        }}
      >
        {/* Node 1: RAW LOGS */}
        <PipelineNode
          id="raw"
          label="RAW LOGS"
          description="Untrusted wire"
          status={getNodeStatus('raw')}
          isSelected={selectedNodeId === 'raw'}
          onClick={() => onSelectNode('raw')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'raw'}
          durationMs={stageDurationMs}
          animKey={`raw-${animatingStage}`}
        />

        {/* Node 2: GATEWAY */}
        <PipelineNode
          id="gateway"
          label="GATEWAY"
          description="Security perimeter"
          status={getNodeStatus('gateway')}
          isSelected={selectedNodeId === 'gateway'}
          onClick={() => onSelectNode('gateway')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'gateway'}
          durationMs={stageDurationMs}
          animKey={`gateway-${animatingStage}`}
        />

        {/* Node 3: M1 INGESTION */}
        <PipelineNode
          id="m1"
          label="M1 INGESTION"
          description="Raw vault & SHA-256"
          status={getNodeStatus('m1')}
          isSelected={selectedNodeId === 'm1'}
          onClick={() => onSelectNode('m1')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'm1'}
          durationMs={stageDurationMs}
          animKey={`m1-${animatingStage}`}
        />

        {/* Node 4: KAFKA */}
        <PipelineNode
          id="kafka"
          label="KAFKA"
          description="Event stream broker"
          status={getNodeStatus('kafka')}
          isSelected={selectedNodeId === 'kafka'}
          onClick={() => onSelectNode('kafka')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'kafka'}
          durationMs={stageDurationMs}
          animKey={`kafka-${animatingStage}`}
        />

        {/* Node 5: M2 PARSER */}
        <PipelineNode
          id="m2"
          label="M2 PARSER"
          description="Vendor grammar"
          status={getNodeStatus('m2')}
          isSelected={selectedNodeId === 'm2'}
          onClick={() => onSelectNode('m2')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'm2'}
          durationMs={stageDurationMs}
          animKey={`m2-${animatingStage}`}
        />

        {/* Node 6: M3 NORMALIZER */}
        <PipelineNode
          id="m3"
          label="M3 NORMALIZER"
          description="Schema validation"
          status={getNodeStatus('m3')}
          isSelected={selectedNodeId === 'm3'}
          onClick={() => onSelectNode('m3')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'm3'}
          durationMs={stageDurationMs}
          animKey={`m3-${animatingStage}`}
        />

        {/* Node 7: M4 ENRICHMENT */}
        <PipelineNode
          id="m4"
          label="M4 ENRICHMENT"
          description="Context & threat intel"
          status={getNodeStatus('m4')}
          isSelected={selectedNodeId === 'm4'}
          onClick={() => onSelectNode('m4')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'm4'}
          durationMs={stageDurationMs}
          animKey={`m4-${animatingStage}`}
        />

        {/* Node 8: M5 ROUTING */}
        <PipelineNode
          id="m5"
          label="M5 ROUTING"
          description="Policy router"
          status={getNodeStatus('m5')}
          isSelected={selectedNodeId === 'm5'}
          onClick={() => onSelectNode('m5')}
        />

        <PipelineConnector
          isAnimating={animatingStage === 'm5'}
          durationMs={stageDurationMs}
          animKey={`m5-${animatingStage}`}
        />

        {/* Node 9: DESTINATIONS */}
        <PipelineNode
          id="destinations"
          label="DESTINATIONS"
          description="OpenSearch & Lake"
          status={getNodeStatus('destinations')}
          isSelected={selectedNodeId === 'destinations'}
          onClick={() => onSelectNode('destinations')}
        />
      </div>
    </div>
  )
}
