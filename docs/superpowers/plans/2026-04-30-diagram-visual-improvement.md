# Diagram Visual Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the visual aesthetics of generated diagrams by adjusting prompt constraints, injecting a custom Mermaid theme, and redesigning the HTML container.

**Architecture:** We are updating the text constraints in the LLM prompts and heavily modifying the HTML/CSS templates used by the backend `mermaid_renderer.py` and `diagram_agent.py` to use modern "Glassmorphism" styling and educational color palettes.

**Tech Stack:** Python, Playwright, Mermaid.js, HTML/CSS.

---

### Task 1: Update Diagram Prompts for Better Structure

**Files:**
- Modify: `server/app/resource/prompts/workers/diagram.md`
- Modify: `server/app/resource/worker_agents/diagram_agent.py`

- [ ] **Step 1: Update the markdown prompt**

Modify `server/app/resource/prompts/workers/diagram.md`. Under the `## 字段限制` (Field Constraints) section, update the constraints to enforce shorter labels and better structure.

Run `replace` tool on `server/app/resource/prompts/workers/diagram.md`:

```markdown
<<<<
## 字段限制

- title: 不超过 20 个字
- summary: 不超过 50 个字
- label: 不超过 16 个字
- description: 不超过 40 个字
- 节点数量控制在 3 到 8 个左右
====
## 字段限制

- title: 不超过 20 个字
- summary: 不超过 50 个字
- label: 极其简短，不超过 10 个字。如果有较长文字，请将其放在 description 中，或者在 label 中使用 `<br/>` 进行人为换行。
- description: 不超过 40 个字
- 节点数量: 控制在 5 到 12 个左右，确保图表结构丰富但不过于拥挤。
>>>>
```

- [ ] **Step 2: Update the fallback prompt in DiagramAgent**

Modify `server/app/resource/worker_agents/diagram_agent.py` to match the new constraints in the `_load_prompt` method.

Run `replace` tool on `server/app/resource/worker_agents/diagram_agent.py`:

```python
<<<<
- title 不超过 20 个字
- summary 不超过 50 个字
- label 不超过 16 个字
- description 不超过 40 个字
- 节点数量控制在 3 到 8 个左右"""
====
- title 不超过 20 个字
- summary 不超过 50 个字
- label 极其简短，不超过 10 个字。如果有较长文字，使用 <br/> 换行或放入 description
- description 不超过 40 个字
- 节点数量控制在 5 到 12 个左右，确保结构丰富"""
>>>>
```

- [ ] **Step 3: Commit**

```bash
git add server/app/resource/prompts/workers/diagram.md server/app/resource/worker_agents/diagram_agent.py
git commit -m "feat(diagram): refine text and node count constraints in prompts"
```

### Task 2: Inject Modern Mermaid Theme & Layout Config

**Files:**
- Modify: `server/app/resource/mermaid_renderer.py`

- [ ] **Step 1: Update MERMAID_HTML_TEMPLATE**

Modify `server/app/resource/mermaid_renderer.py` to inject a custom theme with pastel educational colors, rounded nodes, and smooth curve layouts.

Run `replace` tool on `server/app/resource/mermaid_renderer.py` replacing the `mermaid.initialize` section:

```python
<<<<
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'basis'
      },
      sequence: {
        useMaxWidth: false,
        wrap: true
      },
      state: {
        useMaxWidth: false
      },
      er: {
        useMaxWidth: false
      },
      class: {
        useMaxWidth: false
      },
      gitGraph: {
        useMaxWidth: false
      }
    });
  </script>
====
  <script>
    mermaid.initialize({
      startOnLoad: true,
      theme: 'base',
      themeVariables: {
        primaryColor: '#e0e7ff',
        primaryTextColor: '#3730a3',
        primaryBorderColor: '#a5b4fc',
        lineColor: '#6366f1',
        secondaryColor: '#f3e8ff',
        tertiaryColor: '#ede9fe',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        fontSize: '14px',
        nodeBorder: 'rgba(165, 180, 252, 0.8)'
      },
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: 'monotoneX',
        padding: 20
      },
      sequence: {
        useMaxWidth: false,
        wrap: true,
        actorMargin: 50
      },
      state: {
        useMaxWidth: false,
        nodeSpacing: 50
      },
      er: {
        useMaxWidth: false
      },
      class: {
        useMaxWidth: false
      },
      gitGraph: {
        useMaxWidth: false
      }
    });
  </script>
>>>>
```

- [ ] **Step 2: Commit**

```bash
git add server/app/resource/mermaid_renderer.py
git commit -m "feat(diagram): inject modern educational theme and monotone curves to mermaid renderer"
```

### Task 3: Redesign HTML Wrapper for PNG Rendering

**Files:**
- Modify: `server/app/resource/worker_agents/diagram_agent.py`

- [ ] **Step 1: Update `_build_html_with_png`**

Modify `_build_html_with_png` in `server/app/resource/worker_agents/diagram_agent.py` to use a glassmorphism style and better typography.

Run `replace` tool on `server/app/resource/worker_agents/diagram_agent.py`:

```python
<<<<
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 16px;
      padding: 30px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }}
    .header {{
      text-align: center;
      margin-bottom: 20px;
    }}
    .title {{
      font-size: 24px;
      color: #333;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .summary {{
      font-size: 14px;
      color: #666;
    }}
    .diagram-type {{
      display: inline-block;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      margin-top: 8px;
    }}
    .diagram-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }}
    .diagram-image {{
      max-width: 100%;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .mermaid-source {{
      margin-top: 20px;
      padding: 15px;
      background: #f5f5f5;
      border-radius: 8px;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      overflow-x: auto;
    }}
  </style>
====
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f8fafc;
      background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
      background-size: 20px 20px;
      min-height: 100vh;
      padding: 40px 20px;
      color: #1e293b;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 24px;
      padding: 40px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0, 0, 0, 0.02);
    }}
    .header {{
      text-align: center;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    }}
    .title {{
      font-size: 28px;
      color: #0f172a;
      font-weight: 700;
      letter-spacing: -0.025em;
      margin-bottom: 12px;
    }}
    .summary {{
      font-size: 16px;
      color: #64748b;
      max-width: 800px;
      margin: 0 auto;
      line-height: 1.6;
    }}
    .diagram-type {{
      display: inline-block;
      background: #e0e7ff;
      color: #4f46e5;
      padding: 6px 16px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      margin-top: 16px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .diagram-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
      background: white;
      border-radius: 16px;
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
      border: 1px solid #f1f5f9;
    }}
    .diagram-image {{
      max-width: 100%;
      border-radius: 8px;
      transition: transform 0.3s ease;
    }}
    .diagram-image:hover {{
      transform: scale(1.01);
    }}
    .mermaid-source {{
      margin-top: 30px;
      padding: 20px;
      background: #1e293b;
      color: #e2e8f0;
      border-radius: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 13px;
      white-space: pre-wrap;
      overflow-x: auto;
      box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }}
    details summary {{
      font-weight: 500;
      color: #64748b;
      margin-top: 20px;
      outline: none;
    }}
  </style>
>>>>
```

- [ ] **Step 2: Commit**

```bash
git add server/app/resource/worker_agents/diagram_agent.py
git commit -m "feat(diagram): redesign HTML wrapper for PNG rendering with glassmorphism"
```

### Task 4: Redesign HTML Wrapper for Fallback Rendering

**Files:**
- Modify: `server/app/resource/worker_agents/diagram_agent.py`

- [ ] **Step 1: Update `_build_html_content`**

Apply the same styling logic to `_build_html_content` and ensure the Mermaid fallback rendering uses the new `themeVariables`.

Run `replace` tool on `server/app/resource/worker_agents/diagram_agent.py` replacing the style and script sections in `_build_html_content`:

```python
<<<<
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 16px;
      padding: 30px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }}
    .header {{
      text-align: center;
      margin-bottom: 20px;
    }}
    .title {{
      font-size: 24px;
      color: #333;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .summary {{
      font-size: 14px;
      color: #666;
    }}
    .diagram-type {{
      display: inline-block;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      margin-top: 8px;
    }}
    .diagram-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: {container_height};
      overflow: auto;
    }}
    .mermaid {{
      max-width: 100%;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="title">{title}</h1>
      {f'<p class="summary">{summary}</p>' if summary else ''}
      <span class="diagram-type">{diagram_type}</span>
    </div>
    <div class="diagram-container">
      <pre class="mermaid">
{mermaid_source}
      </pre>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {{
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }},
      sequence: {{
        useMaxWidth: true,
        wrap: true
      }},
      state: {{
        useMaxWidth: true
      }},
      er: {{
        useMaxWidth: true
      }},
      class: {{
        useMaxWidth: true
      }},
      gitGraph: {{
        useMaxWidth: true
      }}
    }});
  </script>
</body>
</html>"""
====
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f8fafc;
      background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
      background-size: 20px 20px;
      min-height: 100vh;
      padding: 40px 20px;
      color: #1e293b;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 24px;
      padding: 40px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0, 0, 0, 0.02);
    }}
    .header {{
      text-align: center;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    }}
    .title {{
      font-size: 28px;
      color: #0f172a;
      font-weight: 700;
      letter-spacing: -0.025em;
      margin-bottom: 12px;
    }}
    .summary {{
      font-size: 16px;
      color: #64748b;
      max-width: 800px;
      margin: 0 auto;
      line-height: 1.6;
    }}
    .diagram-type {{
      display: inline-block;
      background: #e0e7ff;
      color: #4f46e5;
      padding: 6px 16px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      margin-top: 16px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .diagram-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: {container_height};
      overflow: auto;
      padding: 20px;
      background: white;
      border-radius: 16px;
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
      border: 1px solid #f1f5f9;
    }}
    .mermaid {{
      max-width: 100%;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="title">{title}</h1>
      {f'<p class="summary">{summary}</p>' if summary else ''}
      <span class="diagram-type">{diagram_type}</span>
    </div>
    <div class="diagram-container">
      <pre class="mermaid">
{mermaid_source}
      </pre>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'base',
      themeVariables: {{
        primaryColor: '#e0e7ff',
        primaryTextColor: '#3730a3',
        primaryBorderColor: '#a5b4fc',
        lineColor: '#6366f1',
        secondaryColor: '#f3e8ff',
        tertiaryColor: '#ede9fe',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        fontSize: '14px',
        nodeBorder: 'rgba(165, 180, 252, 0.8)'
      }},
      securityLevel: 'loose',
      flowchart: {{
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'monotoneX',
        padding: 20
      }},
      sequence: {{
        useMaxWidth: true,
        wrap: true,
        actorMargin: 50
      }},
      state: {{
        useMaxWidth: true,
        nodeSpacing: 50
      }},
      er: {{
        useMaxWidth: true
      }},
      class: {{
        useMaxWidth: true
      }},
      gitGraph: {{
        useMaxWidth: true
      }}
    }});
  </script>
</body>
</html>"""
>>>>
```

- [ ] **Step 2: Commit**

```bash
git add server/app/resource/worker_agents/diagram_agent.py
git commit -m "feat(diagram): redesign HTML wrapper for fallback mermaid rendering"
```

---
