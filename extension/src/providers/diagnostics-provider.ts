import * as vscode from "vscode";
import type { Issue, Severity } from "../types";

const SEVERITY_MAP: Record<Severity, vscode.DiagnosticSeverity> = {
  error: vscode.DiagnosticSeverity.Error,
  warning: vscode.DiagnosticSeverity.Warning,
  info: vscode.DiagnosticSeverity.Information,
};

export class DiagnosticsProvider implements vscode.Disposable {
  private collection: vscode.DiagnosticCollection;

  constructor() {
    this.collection =
      vscode.languages.createDiagnosticCollection("secureCode");
  }

  update(rootPath: string, issues: Issue[]): void {
    this.collection.clear();

    const byFile = new Map<string, vscode.Diagnostic[]>();

    for (const issue of issues) {
      const filePath = issue.file || rootPath;
      const uri = vscode.Uri.file(filePath);
      const key = uri.toString();

      if (!byFile.has(key)) {
        byFile.set(key, []);
      }

      const range = new vscode.Range(
        Math.max(0, (issue.line ?? 1) - 1),
        0,
        Math.max(0, (issue.line ?? 1) - 1),
        1000
      );

      const diag = new vscode.Diagnostic(
        range,
        `[${issue.analyzer}] ${issue.message}`,
        SEVERITY_MAP[issue.severity]
      );
      diag.source = "SecureCode";
      diag.code = issue.id;

      byFile.get(key)!.push(diag);
    }

    for (const [uriStr, diags] of byFile) {
      this.collection.set(vscode.Uri.parse(uriStr), diags);
    }
  }

  clear(): void {
    this.collection.clear();
  }

  dispose(): void {
    this.collection.dispose();
  }
}
