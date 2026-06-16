import { ComputerCourse, RenderMode, TemplateName } from './videoPlan';

export type TemplateDefinition = {
  name: TemplateName;
  label: string;
  course_scope: ComputerCourse[];
  use_for: string;
  render_cost: 'low' | 'medium' | 'high';
  support_modes: RenderMode[];
  required_fields: string[];
};

export const templateRegistry: Record<TemplateName, TemplateDefinition> = {
  concept_explain: {
    name: 'concept_explain',
    label: '概念讲解',
    course_scope: ['common', 'data_structure', 'operating_system', 'network', 'programming'],
    use_for: '核心概念、定义、特性的结构化讲解',
    render_cost: 'low',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['concept', 'definition', 'features'],
  },
  process_flow: {
    name: 'process_flow',
    label: '流程机制',
    course_scope: ['common', 'operating_system', 'network'],
    use_for: '通用流程与有向图工作流机制步骤演示',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'nodes', 'edges'],
  },
  code_walkthrough: {
    name: 'code_walkthrough',
    label: '代码讲解',
    course_scope: ['programming', 'data_structure'],
    use_for: '代码逐行高亮讲解与内部变量/数据结构状态同步追踪',
    render_cost: 'high',
    support_modes: ['standard', 'detailed'],
    required_fields: ['code', 'steps'],
  },
  question_solution: {
    name: 'question_solution',
    label: '例题解析',
    course_scope: ['common', 'data_structure', 'operating_system', 'network'],
    use_for: '经典例题、计算步骤和最终答案的板书演示',
    render_cost: 'low',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['question', 'steps', 'final_answer'],
  },
  summary_card: {
    name: 'summary_card',
    label: '课堂总结',
    course_scope: ['common', 'data_structure', 'operating_system', 'network', 'programming'],
    use_for: '视频末尾核心考点、知识体系和注意事项总结',
    render_cost: 'low',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'key_points'],
  },
  comparison_table: {
    name: 'comparison_table',
    label: '对比表格',
    course_scope: ['common', 'data_structure', 'operating_system', 'network'],
    use_for: '相似概念对比（如进程 vs 线程，TCP vs UDP）',
    render_cost: 'low',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'left', 'right', 'conclusion'],
  },
  linear_structure_demo: {
    name: 'linear_structure_demo',
    label: '线性结构演示',
    course_scope: ['data_structure'],
    use_for: '栈、队列、数组等线性存储的操作动态演示',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['structure', 'title', 'operations'],
  },
  linked_list_demo: {
    name: 'linked_list_demo',
    label: '链表操作演示',
    course_scope: ['data_structure'],
    use_for: '单链表/双链表的插入、删除、指针重定向动态演示',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'nodes', 'links', 'operations'],
  },
  tree_graph_traversal: {
    name: 'tree_graph_traversal',
    label: '树图遍历演示',
    course_scope: ['data_structure'],
    use_for: '二叉树、图结构的前中后序/BFS/DFS遍历动画演示',
    render_cost: 'high',
    support_modes: ['standard', 'detailed'],
    required_fields: ['title', 'structure_type', 'nodes', 'steps'],
  },
  process_state_transition: {
    name: 'process_state_transition',
    label: '进程状态转换',
    course_scope: ['operating_system'],
    use_for: '进程三状态/五状态在就绪、运行、阻塞等状态间转换的触发过程演示',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'states', 'transitions', 'steps'],
  },
  cpu_scheduling_demo: {
    name: 'cpu_scheduling_demo',
    label: 'CPU调度模拟',
    course_scope: ['operating_system'],
    use_for: 'SJF/FCFS/RR 调度过程的就绪队列排队、甘特图和时间指标展示',
    render_cost: 'high',
    support_modes: ['standard', 'detailed'],
    required_fields: ['title', 'processes', 'schedule_order', 'metrics'],
  },
  protocol_sequence: {
    name: 'protocol_sequence',
    label: '协议时序图',
    course_scope: ['network'],
    use_for: 'TCP三次握手/四次挥手、HTTP请求等通信实体报文交互过程',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'participants', 'messages'],
  },
  call_stack_demo: {
    name: 'call_stack_demo',
    label: '函数调用栈',
    course_scope: ['programming'],
    use_for: '递归、函数多层嵌套执行时内存调用栈进栈出栈的动态演示',
    render_cost: 'medium',
    support_modes: ['quick', 'standard', 'detailed'],
    required_fields: ['title', 'stack_frames'],
  },
};
