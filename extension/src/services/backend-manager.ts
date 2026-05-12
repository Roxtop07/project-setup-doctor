import * as vscode from "vscode";
import { ChildProcess, spawn } from "child_process";
import { accessSync, constants, existsSync } from "fs";
import * as path from "path";
import { BackendClient } from "./backend-client";

export class BackendManager implements vscode.Disposable {
  private process: ChildProcess | null = null;
  private client: BackendClient;
  private outputChannel: vscode.OutputChannel;
  private ready = false;
  private disposed = false;

  constructor(outputChannel: vscode.OutputChannel) {
    this.client = new BackendClient();
    this.outputChannel = outputChannel;
  }

  get isReady(): boolean {
    return this.ready;
  }

  getClient(): BackendClient {
    return this.client;
  }

  async start(): Promise<void> {
    if (await this.isBackendRunning()) {
      this.ready = true;
      this.outputChannel.appendLine(
        "Backend already running, connecting to existing instance."
      );
      return;
    }

    const port = vscode.workspace
      .getConfiguration("secureCode")
      .get<number>("backendPort", 18120);

    const binaryPath = this.findBinary();
    if (binaryPath) {
      this.outputChannel.appendLine(
        `Starting backend (binary mode) on port ${port}...`
      );
      this.spawnBinary(binaryPath, port);
    } else {
      this.outputChannel.appendLine(
        "Bundled binary not found, falling back to Python..."
      );
      await this.spawnPython(port);
    }

    this.attachProcessHandlers();
    await this.waitForReady(15000);
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill("SIGTERM");
      this.process = null;
    }
    this.ready = false;
  }

  dispose(): void {
    this.disposed = true;
    this.stop();
  }

  private findBinary(): string | null {
    const platform = process.platform;
    const arch = process.arch;
    const binaryName =
      platform === "win32" ? "securecode-backend.exe" : "securecode-backend";

    const binDir = path.join(
      __dirname,
      "..",
      "bin",
      `${platform}-${arch}`
    );
    const binaryPath = path.join(binDir, binaryName);

    if (!existsSync(binaryPath)) return null;

    if (platform !== "win32") {
      try {
        accessSync(binaryPath, constants.X_OK);
      } catch {
        return null;
      }
    }

    this.outputChannel.appendLine(`Found binary: ${binaryPath}`);
    return binaryPath;
  }

  private spawnBinary(binaryPath: string, port: number): void {
    this.process = spawn(
      binaryPath,
      ["--host", "127.0.0.1", "--port", String(port)],
      {
        env: { ...process.env },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
  }

  private async spawnPython(port: number): Promise<void> {
    const backendPath = path.join(__dirname, "..", "..", "..", "backend");

    if (!existsSync(path.join(backendPath, "main.py"))) {
      throw new Error(
        "Backend not found. Reinstall the extension or install Python 3.10+."
      );
    }

    const pythonCmd = await this.findPython();
    if (!pythonCmd) {
      throw new Error(
        "Python 3.10+ not found. Install Python and ensure it is on PATH."
      );
    }

    this.outputChannel.appendLine(
      `Starting backend (Python mode): ${pythonCmd} on port ${port}...`
    );

    this.process = spawn(
      pythonCmd,
      [
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        String(port),
        "--log-level",
        "warning",
      ],
      {
        cwd: backendPath,
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
  }

  private attachProcessHandlers(): void {
    if (!this.process) return;

    this.process.stdout?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(data.toString().trim());
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(data.toString().trim());
    });

    this.process.on("error", (err) => {
      this.ready = false;
      this.outputChannel.appendLine(`Backend process error: ${err.message}`);
    });

    this.process.on("exit", (code, signal) => {
      this.ready = false;
      if (!this.disposed) {
        this.outputChannel.appendLine(
          `Backend exited (code=${code}, signal=${signal})`
        );
      }
    });
  }

  private async findPython(): Promise<string | null> {
    const candidates = ["python3", "python"];
    const { execSync } = await import("child_process");

    for (const cmd of candidates) {
      try {
        const version = execSync(`${cmd} --version 2>&1`, {
          encoding: "utf-8",
          timeout: 5000,
        }).trim();
        const match = version.match(/(\d+)\.(\d+)/);
        if (match) {
          const major = parseInt(match[1], 10);
          const minor = parseInt(match[2], 10);
          if (major >= 3 && minor >= 10) {
            this.outputChannel.appendLine(`Found ${cmd}: ${version}`);
            return cmd;
          }
        }
      } catch {
        continue;
      }
    }
    return null;
  }

  private async isBackendRunning(): Promise<boolean> {
    try {
      await this.client.checkHealth();
      return true;
    } catch {
      return false;
    }
  }

  private async waitForReady(timeoutMs: number): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (this.disposed) return;
      if (await this.isBackendRunning()) {
        this.ready = true;
        this.outputChannel.appendLine("Backend is ready.");
        return;
      }
      await new Promise((r) => setTimeout(r, 500));
    }
    throw new Error(
      "Backend failed to start within 15s. Check the SecureCode output channel."
    );
  }
}
