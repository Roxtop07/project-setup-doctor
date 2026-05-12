import * as vscode from "vscode";
import { ChildProcess, spawn } from "child_process";
import { accessSync, constants, existsSync } from "fs";
import * as path from "path";
import { BackendClient } from "./backend-client";

const MAX_RESTART_ATTEMPTS = 3;
const RESTART_DELAY_MS = 2000;

export class BackendManager implements vscode.Disposable {
  private process: ChildProcess | null = null;
  private client: BackendClient;
  private outputChannel: vscode.OutputChannel;
  private ready = false;
  private disposed = false;
  private restartCount = 0;
  private restartTimer: ReturnType<typeof setTimeout> | undefined;

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

  async ensureReady(): Promise<void> {
    if (this.ready) return;

    if (await this.isBackendRunning()) {
      this.ready = true;
      return;
    }

    await this.start();
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
    this.restartCount = 0;
  }

  async stop(): Promise<void> {
    if (this.restartTimer) {
      clearTimeout(this.restartTimer);
      this.restartTimer = undefined;
    }
    if (this.process) {
      const proc = this.process;
      this.process = null;
      proc.kill("SIGTERM");
      setTimeout(() => {
        try {
          proc.kill("SIGKILL");
        } catch {
          // already dead
        }
      }, 3000);
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
    const backendPath = path.join(__dirname, "..", "..", "backend");

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
      this.scheduleRestart();
    });

    this.process.on("exit", (code, signal) => {
      this.ready = false;
      if (!this.disposed) {
        this.outputChannel.appendLine(
          `Backend exited (code=${code}, signal=${signal})`
        );
        this.scheduleRestart();
      }
    });
  }

  private scheduleRestart(): void {
    if (this.disposed) return;
    if (this.restartCount >= MAX_RESTART_ATTEMPTS) {
      this.outputChannel.appendLine(
        `Backend crashed ${MAX_RESTART_ATTEMPTS} times. Not restarting — check the SecureCode output channel.`
      );
      vscode.window
        .showErrorMessage(
          "SecureCode backend keeps crashing. Check output for details.",
          "Show Output"
        )
        .then((action) => {
          if (action === "Show Output") {
            this.outputChannel.show();
          }
        });
      return;
    }

    this.restartCount++;
    const delay = RESTART_DELAY_MS * this.restartCount;
    this.outputChannel.appendLine(
      `Restarting backend in ${delay}ms (attempt ${this.restartCount}/${MAX_RESTART_ATTEMPTS})...`
    );

    this.restartTimer = setTimeout(async () => {
      try {
        await this.start();
        this.outputChannel.appendLine("Backend restarted successfully.");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        this.outputChannel.appendLine(`Backend restart failed: ${msg}`);
      }
    }, delay);
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
