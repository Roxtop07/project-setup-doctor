import * as vscode from "vscode";
import * as fs from "fs/promises";
import * as path from "path";
import type { ScanCache } from "../services/scan-cache";

export function registerExportReportCommand(
  context: vscode.ExtensionContext,
  cache: ScanCache
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "secureCode.exportReport",
      async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) return;

        const cached = cache.get(folders[0].uri.fsPath);
        if (!cached) {
          vscode.window.showWarningMessage("No scan results. Run a scan first.");
          return;
        }

        const uri = await vscode.window.showSaveDialog({
          defaultUri: vscode.Uri.file(
            path.join(folders[0].uri.fsPath, "securecode-report.json")
          ),
          filters: { JSON: ["json"] },
        });

        if (!uri) return;

        await fs.writeFile(
          uri.fsPath,
          JSON.stringify(cached, null, 2),
          "utf-8"
        );

        vscode.window.showInformationMessage(
          `Report exported to ${path.basename(uri.fsPath)}`
        );
      }
    )
  );
}
