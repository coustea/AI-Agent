import { TeachingVideoScene, RenderMode, TemplateName } from '../schema/videoPlan';
import { renderConceptExplain } from '../templates/conceptExplain';
import { renderProcessFlow } from '../templates/processFlow';
import { renderCodeWalkthrough } from '../templates/codeWalkthrough';
import { renderQuestionSolution } from '../templates/questionSolution';
import { renderSummaryCard } from '../templates/summaryCard';
import { renderComparisonTable } from '../templates/comparisonTable';
import { renderLinearStructureDemo } from '../templates/linearStructureDemo';
import { renderLinkedListDemo } from '../templates/linkedListDemo';
import { renderTreeGraphTraversal } from '../templates/treeGraphTraversal';
import { renderProcessStateTransition } from '../templates/processStateTransition';
import { renderCpuSchedulingDemo } from '../templates/cpuSchedulingDemo';
import { renderProtocolSequence } from '../templates/protocolSequence';
import { renderCallStackDemo } from '../templates/callStackDemo';
import { renderErrorScene } from './ErrorScene';

type TemplateRenderer = (view: any, scene: TeachingVideoScene, mode: RenderMode) => Generator<void, void, void>;

const templateRenderers: Record<TemplateName, TemplateRenderer> = {
  concept_explain: renderConceptExplain,
  process_flow: renderProcessFlow,
  code_walkthrough: renderCodeWalkthrough,
  question_solution: renderQuestionSolution,
  summary_card: renderSummaryCard,
  comparison_table: renderComparisonTable,
  linear_structure_demo: renderLinearStructureDemo,
  linked_list_demo: renderLinkedListDemo,
  tree_graph_traversal: renderTreeGraphTraversal,
  process_state_transition: renderProcessStateTransition,
  cpu_scheduling_demo: renderCpuSchedulingDemo,
  protocol_sequence: renderProtocolSequence,
  call_stack_demo: renderCallStackDemo,
};

export function registerTemplate(name: TemplateName, renderer: TemplateRenderer) {
  templateRenderers[name] = renderer;
}

export function* renderScene(
  view: any,
  scene: TeachingVideoScene,
  mode: RenderMode
) {
  const renderer = templateRenderers[scene.template];
  try {
    if (renderer) {
      yield* renderer(view, scene, mode);
    } else {
      yield* renderErrorScene(view, {
        title: scene.title,
        errorMessage: `Template "${scene.template}" is not registered or supported by this renderer.`,
        duration: scene.duration_seconds,
      });
    }
  } catch (error: any) {
    yield* renderErrorScene(view, {
      title: scene.title,
      errorMessage: `Runtime error while rendering: ${error?.message || String(error)}`,
      duration: scene.duration_seconds,
    });
  }
}
