import * as vscode from "vscode";
import type {
  AIConfigRequest,
  AIProviderName,
  AutoFixResult,
  BackendStatus,
  ScanResult,
} from "../types";

export class BackendClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = this.buildBaseUrl();
  }

  private buildBaseUrl(): string {
    const port = vscode.workspace
      .getConfiguration("secureCode")
      .get<number>("backendPort", 18120);
    return `http://127.0.0.1:${port}`;
  }

  private readAIConfig(): AIConfigRequest | undefined {
    const cfg = vscode.workspace.getConfiguration("secureCode");
    const enabled = cfg.get<boolean>("enableAI", false);
    if (!enabled) {
      return undefined;
    }
    const provider = cfg.get<string>("aiProvider", "openai") as AIProviderName;
    const apiKey = cfg.get<string>("aiApiKey", "");
    const baseUrl = cfg.get<string>("aiBaseUrl", "");
    const model = cfg.get<string>("aiModel", "");
    // Local providers may run without a key; require one for everything else.
    if (provider !== "openai-compatible" && !apiKey) {
      return undefined;
    }
    return {
      provider,
      api_key: apiKey,
      base_url: baseUrl || undefined,
      model: model || undefined,
      enabled: true,
    };
  }

  async checkHealth(): Promise<BackendStatus> {
    return this.request<BackendStatus>("GET", "/health");
  }

  async scan(rootPath: string, incremental = false): Promise<ScanResult> {
    return this.request<ScanResult>("POST", "/scan", {
      root_path: rootPath,
      incremental,
      ai_config: this.readAIConfig(),
    });
  }

  async getHealthScore(rootPath: string): Promise<ScanResult> {
    return this.request<ScanResult>("POST", "/health-score", {
      root_path: rootPath,
      ai_config: this.readAIConfig(),
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
    body?: unknown,
    retries = 2
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= retries; attempt++) {
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
      } catch (err: unknown) {
        lastError = err instanceof Error ? err : new Error(String(err));

        if (lastError.name === "AbortError") {
          throw new Error(
            "Request timed out. The backend may be overloaded or unresponsive."
          );
        }

        const isConnectionError =
          lastError.message === "fetch failed" ||
          lastError.message.includes("ECONNREFUSED") ||
          lastError.message.includes("ECONNRESET") ||
          lastError.cause !== undefined;

        if (isConnectionError && attempt < retries) {
          await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
          continue;
        }

        if (isConnectionError) {
          throw new Error(
            "Cannot connect to the SecureCode backend. It may still be starting — try again in a few seconds, or check the SecureCode output channel for errors."
          );
        }

        throw lastError;
      } finally {
        clearTimeout(timeout);
      }
    }

    throw lastError ?? new Error("Request failed");
  }
}
