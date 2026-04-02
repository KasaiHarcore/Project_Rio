"use client"

import React, { useRef, useMemo, useState, useCallback, useEffect } from "react"
import { Canvas, useFrame, ThreeEvent } from "@react-three/fiber"
import { OrbitControls, Text, Line } from "@react-three/drei"
import { DoubleSide } from "three"
import type { Mesh } from "three"
import type { NoteGraphNode, NoteGraphEdge } from "@/features/notes/api"
import { useNoteStore } from "@/features/notes/store"

// ── Force-directed layout ───────────────────────────────────────────────────

interface LayoutNode {
  id: string
  x: number
  y: number
  z: number
  vx: number
  vy: number
  vz: number
  type: string
  label: string
}

function forceLayout(
  nodes: NoteGraphNode[],
  edges: NoteGraphEdge[],
  iterations = 200,
): Map<string, [number, number, number]> {
  const layout: LayoutNode[] = nodes.map((n, i) => ({
    id: n.id,
    x: (Math.random() - 0.5) * 10,
    y: (Math.random() - 0.5) * 10,
    z: (Math.random() - 0.5) * 5,
    vx: 0,
    vy: 0,
    vz: 0,
    type: n.type,
    label: n.label,
  }))

  const idxMap = new Map<string, number>()
  layout.forEach((n, i) => idxMap.set(n.id, i))

  for (let iter = 0; iter < iterations; iter++) {
    const alpha = 1 - iter / iterations
    const repulsion = 8 * alpha
    const attraction = 0.05 * alpha
    const damping = 0.85

    // Repulsive force between all pairs
    for (let i = 0; i < layout.length; i++) {
      for (let j = i + 1; j < layout.length; j++) {
        const a = layout[i]
        const b = layout[j]
        let dx = a.x - b.x
        let dy = a.y - b.y
        let dz = a.z - b.z
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
        const force = repulsion / (dist * dist)
        dx = (dx / dist) * force
        dy = (dy / dist) * force
        dz = (dz / dist) * force
        a.vx += dx; a.vy += dy; a.vz += dz
        b.vx -= dx; b.vy -= dy; b.vz -= dz
      }
    }

    // Attractive force along edges
    for (const edge of edges) {
      const ai = idxMap.get(edge.source_id)
      const bi = idxMap.get(edge.target_id)
      if (ai === undefined || bi === undefined) continue
      const a = layout[ai]
      const b = layout[bi]
      const dx = b.x - a.x
      const dy = b.y - a.y
      const dz = b.z - a.z
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
      const force = attraction * dist
      a.vx += (dx / dist) * force
      a.vy += (dy / dist) * force
      a.vz += (dz / dist) * force
      b.vx -= (dx / dist) * force
      b.vy -= (dy / dist) * force
      b.vz -= (dz / dist) * force
    }

    // Apply velocity
    for (const n of layout) {
      n.vx *= damping; n.vy *= damping; n.vz *= damping
      n.x += n.vx; n.y += n.vy; n.z += n.vz
    }
  }

  const result = new Map<string, [number, number, number]>()
  for (const n of layout) {
    result.set(n.id, [n.x, n.y, n.z])
  }
  return result
}

// ── Colors ──────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  note: "#f43f5e",       // rose-500
  collection: "#10b981", // emerald-500
  document: "#3b82f6",   // blue-500
  artifact: "#a855f7",   // purple-500
  media: "#f59e0b",      // amber-500
  url: "#6b7280",        // gray-500
}

function getColor(type: string): string {
  return TYPE_COLORS[type] ?? "#6b7280"
}

// ── GraphNode3D ─────────────────────────────────────────────────────────────

interface GraphNode3DProps {
  position: [number, number, number]
  node: NoteGraphNode
  isSelected: boolean
  isHighlighted: boolean
  onSelect: (id: string) => void
  onHover: (id: string | null) => void
}

function GraphNode3D({
  position,
  node,
  isSelected,
  isHighlighted,
  onSelect,
  onHover,
}: GraphNode3DProps) {
  const meshRef = useRef<Mesh>(null)
  const color = getColor(node.type)
  const scale = node.type === "collection" ? 0.55 : node.type === "note" ? 0.3 : 0.22
  const finalScale = isSelected ? scale * 1.5 : isHighlighted ? scale * 1.25 : scale

  useFrame((_, delta) => {
    if (!meshRef.current) return
    // Gentle float
    meshRef.current.rotation.y += delta * 0.3
  })

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        scale={finalScale}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation()
          onSelect(node.id)
        }}
        onPointerOver={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation()
          onHover(node.id)
          document.body.style.cursor = "pointer"
        }}
        onPointerOut={() => {
          onHover(null)
          document.body.style.cursor = "auto"
        }}
      >
        {node.type === "collection" ? (
          <dodecahedronGeometry args={[1, 0]} />
        ) : node.type === "note" ? (
          <octahedronGeometry args={[1, 0]} />
        ) : node.type === "document" ? (
          <boxGeometry args={[1.4, 1.8, 0.3]} />
        ) : (
          <sphereGeometry args={[1, 16, 16]} />
        )}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.8 : isHighlighted ? 0.5 : 0.2}
          transparent
          opacity={isHighlighted || isSelected ? 1 : 0.85}
          roughness={0.4}
          metalness={0.3}
        />
      </mesh>

      {/* Glow ring on select */}
      {isSelected && (
        <mesh scale={finalScale * 2}>
          <ringGeometry args={[0.9, 1.1, 32]} />
          <meshBasicMaterial color={color} transparent opacity={0.3} side={DoubleSide} />
        </mesh>
      )}

      {/* Label */}
      <Text
        position={[0, -finalScale - 0.3, 0]}
        fontSize={0.25}
        color={isSelected || isHighlighted ? "#ffffff" : "#9ca3af"}
        anchorX="center"
        anchorY="top"
        maxWidth={3}
      >
        {node.label.length > 24 ? node.label.slice(0, 22) + "…" : node.label}
      </Text>
    </group>
  )
}

// ── GraphEdge3D ─────────────────────────────────────────────────────────────

interface GraphEdge3DProps {
  from: [number, number, number]
  to: [number, number, number]
  color: string
  highlighted: boolean
}

function GraphEdge3D({ from, to, color, highlighted }: GraphEdge3DProps) {
  return (
    <Line
      points={[from, to]}
      color={highlighted ? "#ffffff" : color}
      lineWidth={highlighted ? 2 : 1}
      transparent
      opacity={highlighted ? 0.8 : 0.25}
    />
  )
}

// ── Scene ───────────────────────────────────────────────────────────────────

interface GraphSceneProps {
  nodes: NoteGraphNode[]
  edges: NoteGraphEdge[]
  selectedId: string | null
  onSelectNode: (id: string | null) => void
}

function GraphScene({ nodes, edges, selectedId, onSelectNode }: GraphSceneProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const positions = useMemo(
    () => forceLayout(nodes, edges),
    [nodes, edges],
  )

  // Determine which nodes are connected to the selected/hovered node
  const activeId = selectedId ?? hoveredId
  const connectedIds = useMemo(() => {
    if (!activeId) return new Set<string>()
    const ids = new Set<string>()
    for (const e of edges) {
      if (e.source_id === activeId) ids.add(e.target_id)
      if (e.target_id === activeId) ids.add(e.source_id)
    }
    ids.add(activeId)
    return ids
  }, [activeId, edges])

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, -10, -5]} intensity={0.3} color="#f43f5e" />

      {/* Edges */}
      {edges.map((edge, i) => {
        const from = positions.get(edge.source_id)
        const to = positions.get(edge.target_id)
        if (!from || !to) return null
        const highlighted =
          connectedIds.has(edge.source_id) && connectedIds.has(edge.target_id)
        return (
          <GraphEdge3D
            key={`e-${i}`}
            from={from}
            to={to}
            color={getColor(edge.target_type)}
            highlighted={highlighted}
          />
        )
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const pos = positions.get(node.id)
        if (!pos) return null
        return (
          <GraphNode3D
            key={node.id}
            position={pos}
            node={node}
            isSelected={selectedId === node.id}
            isHighlighted={connectedIds.has(node.id)}
            onSelect={(id) => onSelectNode(selectedId === id ? null : id)}
            onHover={setHoveredId}
          />
        )
      })}

      <OrbitControls
        enableDamping
        dampingFactor={0.1}
        rotateSpeed={0.5}
        zoomSpeed={0.8}
        minDistance={3}
        maxDistance={50}
      />
    </>
  )
}

// ── Detail Panel ────────────────────────────────────────────────────────────

interface DetailPanelProps {
  node: NoteGraphNode | null
  edges: NoteGraphEdge[]
  nodes: NoteGraphNode[]
  onClose: () => void
  onNavigate: (id: string) => void
}

function DetailPanel({ node, edges, nodes, onClose, onNavigate }: DetailPanelProps) {
  if (!node) return null

  const outgoing = edges.filter((e) => e.source_id === node.id)
  const incoming = edges.filter((e) => e.target_id === node.id)
  const nodeMap = useMemo(() => {
    const m = new Map<string, NoteGraphNode>()
    nodes.forEach((n) => m.set(n.id, n))
    return m
  }, [nodes])

  return (
    <div className="absolute top-4 right-4 w-80 max-h-[calc(100%-2rem)] overflow-y-auto rounded-2xl border p-5 backdrop-blur-xl bg-[#0d1117]/90 border-rose-900/30 shadow-2xl z-10">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ backgroundColor: getColor(node.type) }}
          />
          <span className="text-[10px] font-black tracking-widest uppercase text-gray-400">
            {node.type}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 text-sm font-bold"
        >
          ✕
        </button>
      </div>

      <h3 className="text-lg font-bold text-white mb-4 leading-snug">{node.label}</h3>

      {outgoing.length > 0 && (
        <div className="mb-4">
          <p className="text-[10px] font-black tracking-widest uppercase text-gray-500 mb-2">
            {node.type === 'collection' ? 'Contains' : 'Links to'} ({outgoing.length})
          </p>
          <div className="space-y-1.5">
            {outgoing.map((e, i) => {
              const target = nodeMap.get(e.target_id)
              return (
                <button
                  key={i}
                  onClick={() => onNavigate(e.target_id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm hover:bg-rose-900/20 transition-colors"
                >
                  <span
                    className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: getColor(e.target_type) }}
                  />
                  <span className="text-gray-300 truncate">
                    {target?.label ?? e.target_id.slice(0, 8)}
                  </span>
                  <span className="text-[9px] text-gray-600 ml-auto">{e.target_type}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {incoming.length > 0 && (
        <div>
          <p className="text-[10px] font-black tracking-widest uppercase text-gray-500 mb-2">
            {node.type === 'note' ? 'Belongs to / Linked from' : 'Linked from'} ({incoming.length})
          </p>
          <div className="space-y-1.5">
            {incoming.map((e, i) => {
              const source = nodeMap.get(e.source_id)
              return (
                <button
                  key={i}
                  onClick={() => onNavigate(e.source_id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm hover:bg-rose-900/20 transition-colors"
                >
                  <span
                    className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: getColor(source?.type ?? "note") }}
                  />
                  <span className="text-gray-300 truncate">
                    {source?.label ?? e.source_id.slice(0, 8)}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Legend ───────────────────────────────────────────────────────────────────

function GraphLegend() {
  return (
    <div className="absolute bottom-4 left-4 flex gap-4 rounded-xl border px-4 py-2.5 backdrop-blur-xl bg-[#0d1117]/80 border-rose-900/30 z-10">
      {Object.entries(TYPE_COLORS).map(([type, color]) => (
        <div key={type} className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
          <span className="text-[10px] font-bold tracking-wider uppercase text-gray-400">
            {type}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Hook: merge collection data into graph ──────────────────────────────────

function useGraphWithCollections(
  apiNodes: NoteGraphNode[],
  apiEdges: NoteGraphEdge[],
) {
  const collections = useNoteStore((s) => s.collections)
  const notes = useNoteStore((s) => s.notes)

  return useMemo(() => {
    const mergedNodes: NoteGraphNode[] = [...apiNodes]
    const mergedEdges: NoteGraphEdge[] = [...apiEdges]

    const existingNodeIds = new Set(apiNodes.map((n) => n.id))

    // Add collection nodes
    for (const col of collections) {
      const colNodeId = `col-${col.id}`
      if (!existingNodeIds.has(colNodeId)) {
        mergedNodes.push({
          id: colNodeId,
          type: "collection",
          label: col.name,
          metadata: null,
        })
        existingNodeIds.add(colNodeId)
      }
    }

    // Add edges from collections to their notes (M2M: a note can belong to multiple collections)
    for (const note of notes) {
      if (!(note.collectionIds ?? []).length) continue
      // Ensure the note node exists
      if (!existingNodeIds.has(note.id)) {
        mergedNodes.push({
          id: note.id,
          type: "note",
          label: note.title || "Untitled Note",
          metadata: null,
        })
        existingNodeIds.add(note.id)
      }
      for (const colId of (note.collectionIds ?? [])) {
        const colNodeId = `col-${colId}`
        // Add edge: collection → note
        mergedEdges.push({
          source_id: colNodeId,
          target_id: note.id,
          label: "contains",
          target_type: "note",
        })
      }
    }

    // Add edges between collections that share notes with cross-links
    // (collections are related if a note in collection A links to a note in collection B)
    const colNoteMap = new Map<string, Set<string>>()
    for (const note of notes) {
      for (const colId of (note.collectionIds ?? [])) {
        const colNodeId = `col-${colId}`
        if (!colNoteMap.has(colNodeId)) colNoteMap.set(colNodeId, new Set())
        colNoteMap.get(colNodeId)!.add(note.id)
      }
    }

    // Find collection-to-collection relationships via shared note links
    const collectionPairs = new Set<string>()
    for (const edge of apiEdges) {
      let sourceCol: string | null = null
      let targetCol: string | null = null
      for (const [colId, noteIds] of colNoteMap) {
        if (noteIds.has(edge.source_id)) sourceCol = colId
        if (noteIds.has(edge.target_id)) targetCol = colId
      }
      if (sourceCol && targetCol && sourceCol !== targetCol) {
        const pairKey = [sourceCol, targetCol].sort().join('|')
        if (!collectionPairs.has(pairKey)) {
          collectionPairs.add(pairKey)
          mergedEdges.push({
            source_id: sourceCol,
            target_id: targetCol,
            label: "related",
            target_type: "collection",
          })
        }
      }
    }

    return { nodes: mergedNodes, edges: mergedEdges }
  }, [apiNodes, apiEdges, collections, notes])
}

// ── Main component ──────────────────────────────────────────────────────────

interface NoteGraphProps {
  nodes: NoteGraphNode[]
  edges: NoteGraphEdge[]
}

export function NoteGraph({ nodes: apiNodes, edges: apiEdges }: NoteGraphProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { nodes, edges } = useGraphWithCollections(apiNodes, apiEdges)

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId],
  )

  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 rounded-2xl bg-rose-900/20 flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-rose-500 opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="3" />
            <circle cx="4" cy="8" r="2" />
            <circle cx="20" cy="8" r="2" />
            <circle cx="4" cy="16" r="2" />
            <circle cx="20" cy="16" r="2" />
            <line x1="6" y1="8" x2="9" y2="10" />
            <line x1="18" y1="8" x2="15" y2="10" />
            <line x1="6" y1="16" x2="9" y2="14" />
            <line x1="18" y1="16" x2="15" y2="14" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-page-card-title mb-2">No links yet</h3>
        <p className="text-sm text-page-muted max-w-md">
          Add links to your notes using [[Note Title]], [[doc:uuid|Name]], or [label](url) syntax.
          The graph will appear here once you have connected notes.
        </p>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [0, 0, 15], fov: 60 }}
        style={{ background: "transparent" }}
        gl={{ antialias: true, alpha: true }}
      >
        <GraphScene
          nodes={nodes}
          edges={edges}
          selectedId={selectedId}
          onSelectNode={setSelectedId}
        />
      </Canvas>

      <GraphLegend />

      <DetailPanel
        node={selectedNode}
        edges={edges}
        nodes={nodes}
        onClose={() => setSelectedId(null)}
        onNavigate={setSelectedId}
      />

      {/* Stats badge */}
      <div className="absolute top-4 left-4 flex gap-3 rounded-xl border px-4 py-2.5 backdrop-blur-xl bg-[#0d1117]/80 border-rose-900/30 z-10">
        <div className="text-center">
          <p className="text-lg font-black text-white">{nodes.length}</p>
          <p className="text-[9px] font-bold tracking-widest uppercase text-gray-500">Nodes</p>
        </div>
        <div className="w-px bg-rose-900/30" />
        <div className="text-center">
          <p className="text-lg font-black text-white">{edges.length}</p>
          <p className="text-[9px] font-bold tracking-widest uppercase text-gray-500">Links</p>
        </div>
      </div>
    </div>
  )
}
