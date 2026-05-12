import * as vscode from "vscode";
import { BackendManager } from "./services/backend-manager";
import { ScanCache } from "./services/scan-cache";
import { DiagnosticsProvider } from "./providers/diagnostics-provider";
import { StatusBarProvider } from "./providers/status-bar-provider";
import { SidebarProvider } from "./providers/sidebar-provider";
import { registerScanCommand } from "./commands/scan";
import { registerAutoFixCommand } from "./commands/autofix";
import { registerHealthReportCommand } from "./commands/health-report";
import { registerGenerateEnvCommand } from "./commands/generate-env";
import { registerExportReportCommand } from "./commands/export-report";

let backendManager: BackendManager | undefined;

export async function activate(
  context: vscode.ExtensionContext
): Promise<void> {
  const outputChannel = vscode.window.createOutputChannel("SecureCode");
  context.subscriptions.push(outputChannel);

  backendManager = new BackendManager(outputChannel);
  context.subscriptions.push(backendManager);

  const cache = new ScanCache();
  const diagnostics = new DiagnosticsProvider();
  context.subscriptions.push(diagnostics);

  const statusBar = new StatusBarProvider();
  context.subscriptions.push(statusBar);

  const sidebar = new SidebarProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      SidebarProvider.viewType,
      sidebar
    )
  );

  const client = backendManager.getClient();

  registerScanCommand(context, client, backendManager, cache, diagnostics, statusBar, sidebar);
  registerAutoFixCommand(context, client, backendManager, cache);
  registerHealthReportCommand(context, cache);
  registerGenerateEnvCommand(context);
  registerExportReportCommand(context, cache);

  try {
    await backendManager.start();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    outputChannel.appendLine(`Failed to start backend: ${msg}`);
    statusBar.setError("Backend offline");
  }

  const autoScan = vscode.workspace
    .getConfiguration("secureCode")
    .get<boolean>("autoScanOnOpen", true);

  if (autoScan && backendManager.isReady) {
    vscode.commands.executeCommand("secureCode.scanProject");
  }

  registerFileWatcher(context, cache);

  outputChannel.appendLine("Project SecureCode activated.");
}

export function deactivate(): void {
  backendManager?.dispose();
}

function registerFileWatcher(
  context: vscode.ExtensionContext,
  cache: ScanCache
): void {
  const watchPatterns = [
    "**/{package.json,requirements.txt,pyproject.toml}",
    "**/{.env,.env.example,.env.local}",
    "**/Dockerfile",
    "**/docker-compose*.yml",
    "**/README.md",
    "**/*.epl",
    "**/{go.mod,go.sum}",
    "**/{Cargo.toml,Cargo.lock}",
    "**/{pom.xml,build.gradle,build.gradle.kts}",
    "**/{Gemfile,Gemfile.lock}",
    "**/{composer.json,composer.lock}",
    "**/*.csproj",
    "**/Package.swift",
    "**/pubspec.yaml",
    "**/mix.exs",
    "**/CMakeLists.txt",
  ];

  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  const debounceMs = vscode.workspace
    .getConfiguration("secureCode")
    .get<number>("scanDebounceMs", 2000);

  const trigger = () => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      cache.clear();
      vscode.commands.executeCommand("secureCode.scanProject");
    }, debounceMs);
  };

  for (const pattern of watchPatterns) {
    const watcher = vscode.workspace.createFileSystemWatcher(pattern);
    watcher.onDidChange(trigger);
    watcher.onDidCreate(trigger);
    watcher.onDidDelete(trigger);
    context.subscriptions.push(watcher);
  }

  context.subscriptions.push({
    dispose: () => {
      if (debounceTimer) clearTimeout(debounceTimer);
    },
  });
}
