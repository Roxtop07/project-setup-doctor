import * as vscode from "vscode";
import type { ScanCache } from "../services/scan-cache";

export function registerHealthReportCommand(
  context: vscode.ExtensionContext,
  cache: ScanCache
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "projectSetupDoctor.showHealthReport",
      async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) return;

        const cached = cache.get(folders[0].uri.fsPath);
        if (!cached) {
          const action = await vscode.window.showInformationMessage(
            "No scan results available. Scan now?",
            "Scan"
          );
          if (action === "Scan") {
            vscode.commands.executeCommand("projectSetupDoctor.scanProject");
          }
          return;
        }

        const panel = vscode.window.createWebviewPanel(
          "healthReport",
          `Health Report — ${cached.project_info.name}`,
          vscode.ViewColumn.One,
          { enableScripts: false }
        );

        const s = cached.health_score;
        const bd = s.breakdown;
        const pi = cached.project_info;
        const issues = cached.issues;

        panel.webview.html = /*html*/ `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { font-family: var(--vscode-font-family, sans-serif); padding: 24px; color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); }
  h1 { font-size: 20px; margin-bottom: 8px; }
  h2 { font-size: 15px; margin-top: 24px; margin-bottom: 8px; opacity: 0.8; }
  .score { font-size: 48px; font-weight: 700; }
  .grade { font-size: 24px; opacity: 0.7; margin-left: 8px; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { text-align: left; padding: 6px 12px; border-bottom: 1px solid var(--vscode-panel-border, #333); }
  th { font-size: 11px; text-transform: uppercase; opacity: 0.6; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); margin-right: 4px; }
  .error { color: var(--vscode-errorForeground, #f44336); }
  .warning { color: var(--vscode-editorWarning-foreground, #ff9800); }
  .info { color: var(--vscode-editorInfo-foreground, #2196f3); }
</style>
</head>
<body>
  <h1>${pi.name}</h1>
  <div>${pi.types.map((t: string) => `<span class="tag">${t}</span>`).join("")}</div>

  <h2>Health Score</h2>
  <div><span class="score">${Math.round(s.total)}</span><span class="grade">${s.grade}</span></div>

  <h2>Breakdown</h2>
  <table>
    <tr><th>Category</th><th>Score</th></tr>
    <tr><td>Dependency Hygiene</td><td>${Math.round(bd.dependency_hygiene)}/100</td></tr>
    <tr><td>Documentation Quality</td><td>${Math.round(bd.docs_quality)}/100</td></tr>
    <tr><td>Setup Readiness</td><td>${Math.round(bd.setup_readiness)}/100</td></tr>
    <tr><td>Security</td><td>${Math.round(bd.security)}/100</td></tr>
    <tr><td>Environment Completeness</td><td>${Math.round(bd.environment_completeness)}/100</td></tr>
  </table>

  <h2>Issues (${issues.length})</h2>
  <table>
    <tr><th>Severity</th><th>Analyzer</th><th>Message</th><th>File</th></tr>
    ${issues
      .map(
        (i: { severity: string; analyzer: string; message: string; file?: string }) =>
          `<tr><td class="${i.severity}">${i.severity}</td><td>${i.analyzer}</td><td>${i.message}</td><td>${i.file || "—"}</td></tr>`
      )
      .join("")}
  </table>

  <h2>Scan Info</h2>
  <p>Duration: ${cached.scan_duration_ms}ms — ${cached.timestamp}</p>
</body>
</html>`;
      }
    )
  );
}
