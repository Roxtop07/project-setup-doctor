import * as vscode from "vscode";
import type { ScanResult, AutoFixResult, BackendStatus } from "../types";

export class BackendClient {
  private baseUrl: string;

  constructor() {
    const port = vscode.workspace
      .getConfiguration("secureCode")
      .get<number>("backendPort", 18120);
    this.baseUrl = `http://127.0.0.1:${port}`;
  }

  async checkHealth(): Promise<BackendStatus> {
    return this.request<BackendStatus>("GET", "/health");
  }

  async scan(rootPath: string, incremental = false): Promise<ScanResult> {
    return this.request<ScanResult>("POST", "/scan", {
      root_path: rootPath,
      incremental,
    });
  }

  async getHealthScore(rootPath: string): Promise<ScanResult> {
    return this.request<ScanResult>("POST", "/health-score", {
      root_path: rootPath,
    });
  }

  async applyFixes(
    rootPath: string,
    fixIds: string[]
  ): Promise<AutoFixResult> {
    return this.request<AutoFixResult>("POST", "/autofix", {
      root_path: rootPath,
      fix_ids: fixIds,
    });
  }

  async getProjectInfo(rootPath: string): Promise<ScanResult["project_info"]> {
    return this.request<ScanResult["project_info"]>("POST", "/project-info", {
      root_path: rootPath,
    });
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Backend returned ${resp.status}: ${text}`);
      }

      return (await resp.json()) as T;
    } finally {
      clearTimeout(timeout);
    }
  }
}
