import * as vscode from "vscode";
import type { ScanResult } from "../types";

export class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "secureCode.sidebar";
  private view?: vscode.WebviewView;
  private lastResult?: ScanResult;

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtml();

    webviewView.webview.onDidReceiveMessage((msg) => {
      switch (msg.command) {
        case "scan":
          vscode.commands.executeCommand("secureCode.scanProject");
          break;
        case "autofix":
          vscode.commands.executeCommand(
            "secureCode.runAutoFixes",
            msg.fixIds
          );
          break;
        case "export":
          vscode.commands.executeCommand("secureCode.exportReport");
          break;
      }
    });

    if (this.lastResult) {
      this.updateView(this.lastResult);
    }
  }

  updateView(result: ScanResult): void {
    this.lastResult = result;
    this.view?.webview.postMessage({ command: "update", data: result });
  }

  setScanning(): void {
    this.view?.webview.postMessage({ command: "scanning" });
  }

  setError(msg: string): void {
    this.view?.webview.postMessage({ command: "error", message: msg });
  }

  private getHtml(): string {
    return /*html*/ `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {
    --bg: var(--vscode-sideBar-background);
    --fg: var(--vscode-sideBar-foreground);
    --border: var(--vscode-panel-border);
    --badge-error: var(--vscode-errorForeground);
    --badge-warn: var(--vscode-editorWarning-foreground);
    --badge-info: var(--vscode-editorInfo-foreground);
    --btn-bg: var(--vscode-button-background);
    --btn-fg: var(--vscode-button-foreground);
    --btn-hover: var(--vscode-button-hoverBackground);
    --input-bg: var(--vscode-input-background);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--fg);
    background: var(--bg);
    padding: 12px;
  }
  .header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
  .header h2 { font-size: 14px; font-weight: 600; }
  .score-ring {
    width: 72px; height: 72px; margin: 12px auto;
    position: relative; display: flex; align-items: center; justify-content: center;
  }
  .score-ring svg { position: absolute; transform: rotate(-90deg); }
  .score-ring .value { font-size: 20px; font-weight: 700; z-index: 1; }
  .score-ring .grade { font-size: 11px; opacity: 0.7; z-index: 1; margin-top: 2px; }
  .score-center { display: flex; flex-direction: column; align-items: center; }
  .section { margin-bottom: 16px; }
  .section-title {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; opacity: 0.7; margin-bottom: 8px;
    padding-bottom: 4px; border-bottom: 1px solid var(--border);
  }
  .breakdown-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0; font-size: 12px;
  }
  .breakdown-bar {
    width: 60px; height: 4px; background: var(--input-bg);
    border-radius: 2px; overflow: hidden;
  }
  .breakdown-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
  .issue {
    display: flex; gap: 8px; align-items: flex-start;
    padding: 6px 8px; margin-bottom: 4px;
    border-radius: 4px; font-size: 12px;
    background: var(--input-bg);
  }
  .issue .icon { flex-shrink: 0; font-size: 14px; line-height: 1; }
  .issue.error .icon { color: var(--badge-error); }
  .issue.warning .icon { color: var(--badge-warn); }
  .issue.info .icon { color: var(--badge-info); }
  .issue .text { flex: 1; }
  .issue .fix-btn {
    font-size: 10px; padding: 2px 6px; cursor: pointer;
    background: var(--btn-bg); color: var(--btn-fg);
    border: none; border-radius: 3px; white-space: nowrap;
  }
  .issue .fix-btn:hover { background: var(--btn-hover); }
  .btn {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 6px 12px; font-size: 12px; cursor: pointer;
    background: var(--btn-bg); color: var(--btn-fg);
    border: none; border-radius: 4px; margin-right: 6px; margin-bottom: 6px;
  }
  .btn:hover { background: var(--btn-hover); }
  .project-types {
    display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px;
  }
  .tag {
    font-size: 10px; padding: 2px 8px; border-radius: 10px;
    background: var(--btn-bg); color: var(--btn-fg);
  }
  .empty {
    text-align: center; padding: 32px 16px; opacity: 0.6; font-size: 13px;
  }
  .spinner {
    display: inline-block; width: 16px; height: 16px;
    border: 2px solid var(--border); border-top-color: var(--btn-bg);
    border-radius: 50%; animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .counts { display: flex; gap: 12px; margin-bottom: 12px; font-size: 12px; }
  .counts .count { display: flex; align-items: center; gap: 4px; }
</style>
</head>
<body>
  <div id="app">
    <div class="empty">
      <p>Click <b>Scan Project</b> to analyze your workspace.</p>
      <br>
      <button class="btn" onclick="scan()">Scan Project</button>
    </div>
  </div>

<script>
const vscode = acquireVsCodeApi();

function scan() { vscode.postMessage({ command: 'scan' }); }
function autofix(fixIds) { vscode.postMessage({ command: 'autofix', fixIds }); }
function exportReport() { vscode.postMessage({ command: 'export' }); }

function severityIcon(s) {
  return s === 'error' ? '✖' : s === 'warning' ? '⚠' : 'ℹ';
}

function scoreColor(v) {
  if (v >= 80) return '#4caf50';
  if (v >= 50) return '#ff9800';
  return '#f44336';
}

function render(data) {
  const s = data.health_score;
  const pi = data.project_info;
  const issues = data.issues || [];
  const errors = issues.filter(i => i.severity === 'error').length;
  const warnings = issues.filter(i => i.severity === 'warning').length;
  const infos = issues.filter(i => i.severity === 'info').length;

  const circum = 2 * Math.PI * 30;
  const offset = circum - (s.total / 100) * circum;
  const color = scoreColor(s.total);

  const bd = s.breakdown;
  const breakdownRows = [
    ['Dependencies', bd.dependency_hygiene],
    ['Documentation', bd.docs_quality],
    ['Setup Ready', bd.setup_readiness],
    ['Security', bd.security],
    ['Environment', bd.environment_completeness],
  ];

  document.getElementById('app').innerHTML = \`
    <div class="header">
      <h2>SecureCode</h2>
    </div>

    <div class="score-ring">
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r="30" fill="none" stroke="var(--border)" stroke-width="5"/>
        <circle cx="36" cy="36" r="30" fill="none" stroke="\${color}"
          stroke-width="5" stroke-linecap="round"
          stroke-dasharray="\${circum}" stroke-dashoffset="\${offset}"/>
      </svg>
      <div class="score-center">
        <span class="value">\${Math.round(s.total)}</span>
        <span class="grade">\${s.grade}</span>
      </div>
    </div>

    <div class="project-types">
      \${pi.types.map(t => '<span class="tag">' + t + '</span>').join('')}
    </div>

    <div class="counts">
      <span class="count" style="color:var(--badge-error)">✖ \${errors}</span>
      <span class="count" style="color:var(--badge-warn)">⚠ \${warnings}</span>
      <span class="count" style="color:var(--badge-info)">ℹ \${infos}</span>
    </div>

    <div class="section">
      <div class="section-title">Score Breakdown</div>
      \${breakdownRows.map(([label, val]) => \`
        <div class="breakdown-row">
          <span>\${label}</span>
          <div style="display:flex;align-items:center;gap:6px">
            <div class="breakdown-bar">
              <div class="breakdown-bar-fill" style="width:\${val}%;background:\${scoreColor(val)}"></div>
            </div>
            <span>\${Math.round(val)}</span>
          </div>
        </div>
      \`).join('')}
    </div>

    <div class="section">
      <div class="section-title">Issues (\${issues.length})</div>
      \${issues.length === 0 ? '<div style="font-size:12px;opacity:0.6">No issues found!</div>' :
        issues.map(i => \`
          <div class="issue \${i.severity}">
            <span class="icon">\${severityIcon(i.severity)}</span>
            <span class="text">\${i.message}</span>
            \${i.fix ? '<button class="fix-btn" onclick="autofix([\\'' + i.fix.id + '\\'])">Fix</button>' : ''}
          </div>
        \`).join('')}
    </div>

    <div class="section">
      <button class="btn" onclick="scan()">Re-scan</button>
      \${issues.some(i => i.fix) ? '<button class="btn" onclick="autofix(' + JSON.stringify(issues.filter(i=>i.fix).map(i=>i.fix.id)) + ')">Fix All</button>' : ''}
      <button class="btn" onclick="exportReport()">Export JSON</button>
    </div>
  \`;
}

window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.command === 'update') render(msg.data);
  else if (msg.command === 'scanning') {
    document.getElementById('app').innerHTML =
      '<div class="empty"><div class="spinner"></div><p style="margin-top:12px">Scanning project...</p></div>';
  } else if (msg.command === 'error') {
    document.getElementById('app').innerHTML =
      '<div class="empty"><p style="color:var(--badge-error)">' + msg.message + '</p><br><button class="btn" onclick="scan()">Retry</button></div>';
  }
});
</script>
</body>
</html>`;
  }
}
