import React from "react";
import { RichVideoScene, VideoMeta, GlobalStyle } from "./schema/types";
import { SceneDataProvider } from "./components/SceneDataContext";

// Import all scene templates
import { UnknownSceneFallback } from "./scenes/UnknownSceneFallback";
import { TitleIntroPro } from "./scenes/TitleIntroPro";
import { ConceptExplainPro } from "./scenes/ConceptExplainPro";
import { ProcessFlowPro } from "./scenes/ProcessFlowPro";
import { StateMachineLab } from "./scenes/StateMachineLab";
import { DataStructureLab } from "./scenes/DataStructureLab";
import { AlgorithmTraceBoard } from "./scenes/AlgorithmTraceBoard";
import { MemoryLayoutLab } from "./scenes/MemoryLayoutLab";
import { CpuArchitectureLab } from "./scenes/CpuArchitectureLab";
import { NetworkProtocolTimeline } from "./scenes/NetworkProtocolTimeline";
import { LayeredArchitectureScene } from "./scenes/LayeredArchitectureScene";
import { CodeExecutionLab } from "./scenes/CodeExecutionLab";
import { CompareSummaryPro } from "./scenes/CompareSummaryPro";
import { KnowledgeCheckScene } from "./scenes/KnowledgeCheckScene";
// CS Theory templates
import { ArrayLinkedListLab } from "./scenes/ArrayLinkedListLab";
import { StackQueueLab } from "./scenes/StackQueueLab";
import { ProcessStateTransition } from "./scenes/ProcessStateTransition";
import { StorageHierarchy } from "./scenes/StorageHierarchy";

interface SceneRouterProps {
  scene: RichVideoScene;
  meta: VideoMeta;
  globalStyle: GlobalStyle;
  currentSceneIndex: number;
  totalScenes: number;
}

// Router Mapping
const sceneMap: Record<string, React.FC<SceneRouterProps>> = {
  title_intro: TitleIntroPro,
  concept_explain: ConceptExplainPro,
  process_flow: ProcessFlowPro,
  state_machine: StateMachineLab,
  data_structure: DataStructureLab,
  algorithm_trace: AlgorithmTraceBoard,
  memory_layout: MemoryLayoutLab,
  cpu_architecture: CpuArchitectureLab,
  network_protocol: NetworkProtocolTimeline,
  layered_architecture: LayeredArchitectureScene,
  code_execution: CodeExecutionLab,
  compare_summary: CompareSummaryPro,
  knowledge_check: KnowledgeCheckScene,
  // CS Theory templates
  array_linked_list: ArrayLinkedListLab,
  stack_queue: StackQueueLab,
  process_state: ProcessStateTransition,
  storage_hierarchy: StorageHierarchy,
};

export const SceneRouter: React.FC<SceneRouterProps> = (props) => {
  const SceneComponent = sceneMap[props.scene.type] || UnknownSceneFallback;

  return (
    <SceneDataProvider scene={props.scene}>
      <SceneComponent
        scene={props.scene}
        meta={props.meta}
        globalStyle={props.globalStyle}
        currentSceneIndex={props.currentSceneIndex}
        totalScenes={props.totalScenes}
      />
    </SceneDataProvider>
  );
};
