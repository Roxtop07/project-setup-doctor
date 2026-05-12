import * as vscode from "vscode";
import type { BackendClient } from "../services/backend-client";
import type { BackendManager } from "../services/backend-manager";
import type { ScanCache } from "../services/scan-cache";

export function registerAutoFixCommand(
  context: vscode.ExtensionContext,
  client: BackendClient,
  backendManager: BackendManager,
  cache: ScanCache
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "secureCode.runAutoFixes",
      async (fixIds?: string[]) => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) return;

        try {
          await backendManager.ensureReady();
        } catch {
          vscode.window.showErrorMessage(
            "SecureCode backend is not available. Try reloading the window."
          );
          return;
        }

        const rootPath = folders[0].uri.fsPath;
        const cached = cache.get(rootPath);

        if (!fixIds && cached) {
          const available = cached.issues
            .filter((i) => i.fix)
            .map((i) => i.fix!);

          if (available.length === 0) {
            vscode.window.showInformationMessage("No auto-fixes available.");
            return;
          }

          const picks = await vscode.window.showQuickPick(
            available.map((f) => ({
              label: f.description,
              id: f.id,
              picked: true,
            })),
            { canPickMany: true, title: "Select fixes to apply" }
          );

          if (!picks?.length) return;
          fixIds = picks.map((p) => p.id);
        }

        if (!fixIds?.length) {
          vscode.window.showInformationMessage(
            "No fixes selected. Run a scan first."
          );
          return;
        }

        try {
          const result = await client.applyFixes(rootPath, fixIds);
          cache.invalidate(rootPath);

          if (result.failed.length > 0) {
            vscode.window.showWarningMessage(
              `Applied ${result.applied.length} fixes, ${result.failed.length} failed.`
            );
          } else {
            vscode.window.showInformationMessage(
              `Applied ${result.applied.length} fixes successfully.`
            );
          }

          vscode.commands.executeCommand("secureCode.scanProject");
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Unknown error";
          vscode.window.showErrorMessage(`Auto-fix failed: ${msg}`);
        }
      }
    )
  );
}
