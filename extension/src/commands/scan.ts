import * as vscode from "vscode";
import type { BackendClient } from "../services/backend-client";
import type { ScanCache } from "../services/scan-cache";
import type { DiagnosticsProvider } from "../providers/diagnostics-provider";
import type { StatusBarProvider } from "../providers/status-bar-provider";
import type { SidebarProvider } from "../providers/sidebar-provider";
import type { ScanResult } from "../types";

export function registerScanCommand(
  context: vscode.ExtensionContext,
  client: BackendClient,
  cache: ScanCache,
  diagnostics: DiagnosticsProvider,
  statusBar: StatusBarProvider,
  sidebar: SidebarProvider
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "projectSetupDoctor.scanProject",
      async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) {
          vscode.window.showWarningMessage("No workspace folder open.");
          return;
        }

        statusBar.setScanning();
        sidebar.setScanning();

        const results: ScanResult[] = [];

        for (const folder of folders) {
          const rootPath = folder.uri.fsPath;
          try {
            const result = await client.scan(rootPath);
            cache.set(rootPath, result);
            results.push(result);
          } catch (err: unknown) {
            const msg =
              err instanceof Error ? err.message : "Unknown error";
            vscode.window.showErrorMessage(
              `Scan failed for ${folder.name}: ${msg}`
            );
            statusBar.setError("Scan failed");
            sidebar.setError(`Scan failed: ${msg}`);
            return;
          }
        }

        const merged = mergeResults(results);
        diagnostics.update(folders[0].uri.fsPath, merged.issues);
        statusBar.setScore(merged.health_score);
        sidebar.updateView(merged);

        const errorCount = merged.issues.filter(
          (i) => i.severity === "error"
        ).length;
        const warnCount = merged.issues.filter(
          (i) => i.severity === "warning"
        ).length;

        if (errorCount === 0 && warnCount === 0) {
          vscode.window.showInformationMessage(
            `Setup Doctor: Health score ${Math.round(merged.health_score.total)}/100 — no issues found.`
          );
        } else {
          vscode.window.showInformationMessage(
            `Setup Doctor: ${errorCount} errors, ${warnCount} warnings. Score: ${Math.round(merged.health_score.total)}/100`
          );
        }
      }
    )
  );
}

function mergeResults(results: ScanResult[]): ScanResult {
  if (results.length === 1) return results[0];

  const allIssues = results.flatMap((r) => r.issues);
  const avgScore = results.reduce((s, r) => s + r.health_score.total, 0) / results.length;

  const breakdown = {
    dependency_hygiene: avg(results.map((r) => r.health_score.breakdown.dependency_hygiene)),
    docs_quality: avg(results.map((r) => r.health_score.breakdown.docs_quality)),
    setup_readiness: avg(results.map((r) => r.health_score.breakdown.setup_readiness)),
    security: avg(results.map((r) => r.health_score.breakdown.security)),
    environment_completeness: avg(results.map((r) => r.health_score.breakdown.environment_completeness)),
  };

  return {
    project_info: results[0].project_info,
    issues: allIssues,
    health_score: {
      total: avgScore,
      breakdown,
      grade: gradeFromScore(avgScore),
    },
    scan_duration_ms: results.reduce((s, r) => s + r.scan_duration_ms, 0),
    timestamp: new Date().toISOString(),
  };
}

function avg(nums: number[]): number {
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function gradeFromScore(score: number): "A" | "B" | "C" | "D" | "F" {
  if (score >= 90) return "A";
  if (score >= 75) return "B";
  if (score >= 60) return "C";
  if (score >= 40) return "D";
  return "F";
}
