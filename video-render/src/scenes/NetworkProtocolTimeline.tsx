import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { RichVideoScene, GlobalStyle, VideoMeta } from '../schema/types';
import { EduBackground } from '../components/EduBackground';
import { SceneHeader } from '../components/SceneHeader';
import { SubtitleBar } from '../components/SubtitleBar';
import { InfoPanel } from '../components/InfoPanel';
import { getSpringProgress, getSlideInterpolation } from '../utils/animation';
import { useSceneTiming } from '../hooks/useSceneTiming';



interface ProtocolMessage {
  from: string;
  to: string;
  label: string;
  description: string;
  seq?: string;
  ack?: string;
}

interface PacketField {
  name: string;
  meaning: string;
}

interface StateChange {
  participant: string;
  from: string;
  to: string;
}

interface NetworkProtocolTimelineProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

export const NetworkProtocolTimeline: React.FC<NetworkProtocolTimelineProps> = ({
  scene,
  meta,
  globalStyle,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Extract variables
  const protocolName = (scene.visual.protocol_name as string) || '';
  const messages = (scene.visual.messages as ProtocolMessage[]) || [];
  const packetFields = (scene.visual.packet_fields as PacketField[]) || [];
  const stateChanges = (scene.visual.state_changes as StateChange[]) || [];
  const keyPoint = (scene.visual.key_point as string) || '';

  // Determine active message index
  const timing = useSceneTiming(scene);
  const activeMsgIdx = timing.getActiveIndex(messages.length, ['trace_step']);
  const currentMsg = messages[activeMsgIdx];

  // Timing inside current step
  const progress = timing.getStepProgress(messages.length, ['trace_step']);

  // Let's compute current states of participants
  const clientState = stateChanges
    .filter((sc) => sc.participant === 'client' && messages.indexOf(currentMsg) >= stateChanges.indexOf(sc))
    .pop()?.to || 'LISTEN/CLOSED';

  const serverState = stateChanges
    .filter((sc) => sc.participant === 'server' && messages.indexOf(currentMsg) >= stateChanges.indexOf(sc))
    .pop()?.to || 'LISTEN';

  // Positions
  const clientX = 100;
  const serverX = 500;
  const topY = 60;
  const gapY = 80;

  // Packet flight coordinates
  const isFromClient = currentMsg?.from === 'client';
  const packetStartX = isFromClient ? clientX + 80 : serverX;
  const packetEndX = isFromClient ? serverX : clientX + 80;
  const packetY = topY + activeMsgIdx * gapY + progress * gapY;
  const packetX = getSlideInterpolation(progress, 0, 1, packetStartX, packetEndX);

  const sideEntrance = getSpringProgress(frame, fps, 10, 25);

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
        {/* Left: Timing Diagram Canvas */}
        <div className="flex flex-col space-y-6 h-full justify-center">
          <div className="edu-card flex flex-col space-y-4 h-[440px] overflow-hidden">
            <h3 className="text-lg font-bold text-[var(--text-main)] select-none border-b border-[var(--card-border)] pb-2">
              协议交互图: {protocolName}
            </h3>

            {/* Timelines Canvas */}
            <div className="relative flex-1 bg-slate-50/50 rounded-xl overflow-visible p-4">
              {/* Vertical Lanes */}
              {/* Client Lane */}
              <div className="absolute left-[100px] top-4 bottom-4 w-1 bg-blue-200" />
              <div className="absolute left-[80px] top-0 bg-white border border-[var(--card-border)] px-3 py-1 rounded-md text-xs font-extrabold text-[var(--primary)] shadow-sm z-10 select-none">
                客户端 ({clientState})
              </div>

              {/* Server Lane */}
              <div className="absolute left-[500px] top-4 bottom-4 w-1 bg-blue-200" />
              <div className="absolute left-[480px] top-0 bg-white border border-[var(--card-border)] px-3 py-1 rounded-md text-xs font-extrabold text-[var(--primary)] shadow-sm z-10 select-none">
                服务器 ({serverState})
              </div>

              {/* Draw past message lines */}
              {messages.map((msg, idx) => {
                if (idx > activeMsgIdx) return null;
                const isCurrent = idx === activeMsgIdx;
                const isLeftToRight = msg.from === 'client';
                const y1 = topY + idx * gapY;
                const y2 = topY + (idx + 1) * gapY;

                return (
                  <svg key={idx} className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
                    <line
                      x1={isLeftToRight ? clientX + 4 : serverX + 4}
                      y1={y1}
                      x2={isLeftToRight ? serverX + 4 : clientX + 4}
                      y2={isCurrent ? packetY : y2}
                      stroke={isCurrent ? 'var(--primary)' : 'var(--text-muted)'}
                      strokeWidth="2"
                      strokeDasharray={isCurrent ? '4 2' : undefined}
                      markerEnd={!isCurrent ? 'url(#arrow)' : undefined}
                    />
                    <text
                      x={300}
                      y={y1 + gapY / 2 - 4}
                      textAnchor="middle"
                      fill={isCurrent ? 'var(--primary)' : 'var(--text-muted)'}
                      className="text-[10px] font-extrabold font-mono"
                    >
                      {msg.label} {msg.seq ? `(seq=${msg.seq})` : ''} {msg.ack ? `(ack=${msg.ack})` : ''}
                    </text>
                  </svg>
                );
              })}

              {/* Animated flying packet */}
              {currentMsg && (
                <div
                  className="absolute z-20 w-8 h-8 rounded-lg bg-[var(--primary)] text-white shadow-lg border border-white flex items-center justify-center font-mono text-[9px] font-bold"
                  style={{
                    left: packetX - 16,
                    top: packetY - 16,
                  }}
                >
                  ✉
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar explanation panel */}
        <div
          className="h-full flex flex-col justify-center space-y-4"
          style={{
            opacity: sideEntrance,
            transform: `translateX(${getSlideInterpolation(sideEntrance, 0, 1, 45, 0)}px)`,
          }}
        >
          {/* Packet Field Explanation */}
          <div className="edu-card !p-4 flex flex-col space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] border-b border-[var(--card-border)] pb-1 select-none">
              报文字段解析 (Packet Fields)
            </h4>
            <div className="flex flex-col space-y-1.5">
              {packetFields.map((pf, idx) => (
                <div key={idx} className="flex justify-between text-xs">
                  <span className="font-mono font-bold text-[var(--primary)] bg-blue-50 px-1 rounded">{pf.name}</span>
                  <span className="text-[var(--text-muted)] font-medium">{pf.meaning}</span>
                </div>
              ))}
            </div>
          </div>

          <InfoPanel
            title="协议时序要点"
            explanation={currentMsg?.description}
            points={[keyPoint]}
          />
        </div>
      </div>

      <SubtitleBar narration={scene.narration} durationSeconds={scene.duration_seconds} captionWords={scene.caption_words} />
    </AbsoluteFill>
  );
};
