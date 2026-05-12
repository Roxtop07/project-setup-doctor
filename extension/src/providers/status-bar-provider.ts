import * as vscode from "vscode";
import type { HealthScore } from "../types";

export class StatusBarProvider implements vscode.Disposable {
  private item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      50
    );
    this.item.command = "secureCode.showHealthReport";
    this.item.tooltip = "SecureCode - Click to view health report";
    this.setIdle();
    this.item.show();
  }

  setIdle(): void {
    this.item.text = "$(pulse) SecureCode";
    this.item.backgroundColor = undefined;
  }

  setScanning(): void {
    this.item.text = "$(loading~spin) Scanning...";
    this.item.backgroundColor = undefined;
  }

  setScore(score: HealthScore): void {
    const icon =
      score.total >= 80
        ? "$(pass-filled)"
        : score.total >= 50
          ? "$(warning)"
          : "$(error)";
    this.item.text = `${icon} Health: ${Math.round(score.total)}/100 (${score.grade})`;
    this.item.backgroundColor =
      score.total < 50
        ? new vscode.ThemeColor("statusBarItem.errorBackground")
        : undefined;
  }

  setError(msg: string): void {
    this.item.text = `$(error) ${msg}`;
    this.item.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.errorBackground"
    );
  }

  dispose(): void {
    this.item.dispose();
  }
}
