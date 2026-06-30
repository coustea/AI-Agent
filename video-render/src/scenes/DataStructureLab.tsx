import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { DiagramNode } from '../components/DiagramNode';
import { AnimatedArrow } from '../components/AnimatedArrow';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';
import { useSceneTiming } from '../hooks/useSceneTiming';

interface DataNode {
  id: string;
  value: number | string;
}

interface Edge {
  from: string;
  to: string;
}

interface DataStructureLabProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const DataStructureLab: React.FC<DataStructureLabProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const structureType = (scene.visual.structure_type as string) || 'linked_list';
  const initialState = (scene.visual.initial_state as { nodes: DataNode[]; edges: Edge[] }) || { nodes: [], edges: [] };
  const operations = (scene.visual.operations as { action: string; target?: string; new_node?: DataNode; description: string; from?: string; to?: string }[]) || [];
  const pointerLabels = (scene.visual.pointer_labels as { name: string; target: string }[]) || [];
  const complexity = (scene.visual.complexity as { time: string; space: string; condition?: string }) || { time: '', space: '' };
  const invariant = (scene.visual.invariant as string) || '';

  // Determine current operation based on frame timing
  const timing = useSceneTiming(scene);
  const activeOpIdx = timing.getActiveIndex(operations.length, ['trace_step']);
  const currentOp = operations[activeOpIdx];

  // Derive current nodes list and edge lists based on the current operation
  const nodes = [...initialState.nodes];
  let edges = [...initialState.edges];
  let activeNodeId = '';
  let activeEdge: Edge | null = null;

  // Apply operations up to the current operation index to compute current structure state
  for (let i = 0; i <= activeOpIdx; i++) {
    const op = operations[i];
    if (!op) continue;

    if (op.action === 'insert_after' && op.new_node && op.target) {
      // Find insertion index
      const targetIdx = nodes.findIndex(n => n.id === op.target);
      if (targetIdx !== -1) {
        // We'll insert it in the array
        nodes.splice(targetIdx + 1, 0, op.new_node);
        activeNodeId = op.new_node.id;
      }
    } else if (op.action === 'update_pointer' && op.from && op.to) {
      // Modify edges
      edges = edges.filter(e => e.from !== op.from);
      edges.push({ from: op.from, to: op.to });
      activeEdge = { from: op.from, to: op.to };
    }
  }

  // Anim values
  const sideEntrance = getSpringProgress(frame, fps, 10, 25);
  const opEntrance = getSlideInterpolation(
    timing.getStepProgress(operations.length, ['trace_step']),
    0,
    0.2,
    0,
    1,
  );

  return (
    <AbsoluteFill className="p-24 pt-32 overflow-hidden">
      <EduBackground backgroundType={globalStyle.background} />
      <SceneHeader
        course={meta.subject}
        topic={meta.topic}
        sceneTitle={scene.title}
        currentSceneIndex={currentSceneIndex}
        totalScenes={totalScenes}
        progress={frame / durationInFrames}
      />

      <div className="scene-layout-grid w-full h-[calc(100%-40px)] z-10">
        {/* Left: Interactive Data Structure Canvas */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          <div className="edu-card flex flex-col space-y-4 h-[400px]">
            <h3 className="text-lg font-bold text-[var(--text-main)] capitalize flex justify-between items-center select-none border-b border-[var(--card-border)] pb-2">
              <span>数据结构演练: {structureType.replace('_', ' ')}</span>
              <span className="text-xs font-mono font-bold badge-primary px-2 py-0.5 rounded">
                操作: {activeOpIdx + 1} / {operations.length}
              </span>
            </h3>

            {/* Visual Canvas */}
            <div className="relative flex-1 bg-slate-50/50 rounded-xl overflow-visible flex items-center justify-center">
              {/* Linked List Renderer */}
              {structureType === 'linked_list' && (
                <div className="relative w-full h-full flex items-center justify-center">
                  {nodes.map((node, idx) => {
                    const isNew = node.id === activeNodeId;
                    const x = 80 + idx * 160;
                    // Draw new node slightly offset vertically, moving down with animation
                    const y = isNew 
                      ? getSlideInterpolation(opEntrance, 0, 1, 60, 150)
                      : 150;

                    const isActive = node.id === activeNodeId;

                    return (
                      <React.Fragment key={node.id}>
                        {/* Node Card */}
                        <div
                          className="absolute"
                          style={{
                            left: x,
                            top: y,
                          }}
                        >
                          <DiagramNode
                            id={node.id}
                            label={String(node.value)}
                            status={isActive ? 'active' : 'normal'}
                            className="w-20 h-16 flex items-center justify-center font-mono border-2 shadow-md"
                          />
                        </div>

                        {/* Arrow to Next Node */}
                        {idx < nodes.length - 1 && (
                          <AnimatedArrow
                            startX={x + 80}
                            startY={y + 32}
                            endX={x + 160}
                            endY={nodes[idx + 1].id === activeNodeId ? 150 + 32 : 150 + 32}
                            isActive={activeEdge?.from === node.id || nodes[idx + 1].id === activeNodeId}
                          />
                        )}

                        {/* Pointer label helpers (e.g. head, cur) */}
                        {pointerLabels.filter(p => p.target === node.id).map((ptr, pIdx) => (
                          <span
                            key={pIdx}
                            className="absolute bg-orange-500 text-white font-mono text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider shadow-sm z-20"
                            style={{
                              left: x + 10,
                              top: y - 25 - pIdx * 16,
                            }}
                          >
                            {ptr.name} ↓
                          </span>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </div>
              )}

              {/* Stack/Queue/Default fallback */}
              {structureType !== 'linked_list' && (
                <div className="flex space-x-4">
                  {nodes.map((node) => (
                    <DiagramNode
                      key={node.id}
                      id={node.id}
                      label={String(node.value)}
                      status={node.id === activeNodeId ? 'active' : 'normal'}
                      className="w-20 h-20"
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Current Operation Description */}
            {currentOp && (
              <div 
                className="p-3 bg-blue-50/50 border border-blue-100 rounded-xl"
                style={{ opacity: opEntrance }}
              >
                <span className="text-[10px] font-bold text-[var(--primary)] uppercase">当前操作描述</span>
                <p className="text-xs text-[var(--text-muted)] font-medium mt-0.5">{currentOp.description}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right sideboard detail pane */}
        <div
          className="h-full flex flex-col justify-center"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 45, 0)}px)`,
          }}
        >
          <InfoPanel
            title="结构变动 & 复杂度"
            explanation={invariant ? `数据结构不变量: ${invariant}` : undefined}
            points={[
              `时间复杂度: ${complexity.time}`,
              `空间复杂度: ${complexity.space}`,
              complexity.condition ? `适用条件: ${complexity.condition}` : '',
            ].filter(Boolean)}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
