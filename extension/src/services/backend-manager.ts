import * as vscode from "vscode";
import { ChildProcess, spawn, execSync } from "child_process";
import {
  accessSync,
  chmodSync,
  constants,
  existsSync,
  readdirSync,
  statSync,
} from "fs";
import * as path from "path";
import * as net from "net";
import { BackendClient } from "./backend-client";

const MAX_RESTART_ATTEMPTS = 3;
const RESTART_DELAY_MS = 2000;
const STARTUP_TIMEOUT_MS = 30000;

export class BackendManager implements vscode.Disposable {
  private process: ChildProcess | null = null;
  private client: BackendClient;
  private outputChannel: vscode.OutputChannel;
  private ready = false;
  private disposed = false;
  private restartCount = 0;
  private restartTimer: ReturnType<typeof setTimeout> | undefined;
  private lastStderr = "";
  private startMode: "binary" | "python" | "none" = "none";

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

    const portInUse = await this.isPortInUse(port);
    if (portInUse) {
      throw new Error(
        `Port ${port} is already in use by another process. ` +
          `Change the port in Settings → SecureCode → Backend Port, or stop the process using port ${port}.`
      );
    }

    this.lastStderr = "";
    this.startMode = "none";

    const binaryPath = this.findBinary();
    if (binaryPath) {
      this.outputChannel.appendLine(
        `Starting backend (binary mode) on port ${port}...`
      );
      this.startMode = "binary";
      this.spawnBinary(binaryPath, port);
    } else {
      const backendPath = this.findBackendSource();
      if (backendPath) {
        this.outputChannel.appendLine(
          "Bundled binary not found, falling back to Python..."
        );
        this.startMode = "python";
        await this.spawnPython(backendPath, port);
      } else {
        throw new Error(this.buildNoBinaryError());
      }
    }

    this.attachProcessHandlers();
    await this.waitForReady(STARTUP_TIMEOUT_MS);
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

    if (!existsSync(binaryPath)) {
      this.outputChannel.appendLine(`Binary not found at: ${binaryPath}`);
      return null;
    }

    if (platform !== "win32") {
      this.fixPermissions(binDir);
      this.removeQuarantine(binDir);
    }

    this.outputChannel.appendLine(`Found binary: ${binaryPath}`);
    return binaryPath;
  }

  private fixPermissions(binDir: string): void {
    try {
      const entries = this.walkDir(binDir);
      let fixed = 0;
      for (const filePath of entries) {
        try {
          accessSync(filePath, constants.X_OK);
        } catch {
          try {
            chmodSync(filePath, 0o755);
            fixed++;
          } catch {
            // individual file permission fix failed, continue
          }
        }
      }
      if (fixed > 0) {
        this.outputChannel.appendLine(
          `Fixed execute permissions on ${fixed} file(s) in binary directory.`
        );
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      this.outputChannel.appendLine(
        `Warning: Could not fix permissions in binary directory: ${msg}`
      );
    }
  }

  private removeQuarantine(binDir: string): void {
    if (process.platform !== "darwin") return;

    try {
      execSync(
        `xattr -dr com.apple.quarantine "${binDir}" 2>/dev/null`,
        { timeout: 10000 }
      );
      this.outputChannel.appendLine(
        "Removed macOS quarantine attribute from binary directory."
      );
    } catch {
      // Attribute may not exist — that's fine
    }
  }

  private walkDir(dir: string): string[] {
    const results: string[] = [];
    for (const entry of readdirSync(dir)) {
      const fullPath = path.join(dir, entry);
      const stat = statSync(fullPath);
      if (stat.isDirectory()) {
        results.push(...this.walkDir(fullPath));
      } else if (stat.isFile()) {
        results.push(fullPath);
      }
    }
    return results;
  }

  private findBackendSource(): string | null {
    const candidates = [
      path.join(__dirname, "..", "backend"),
      path.join(__dirname, "..", "..", "backend"),
    ];

    for (const candidate of candidates) {
      if (existsSync(path.join(candidate, "main.py"))) {
        return candidate;
      }
    }

    return null;
  }

  private spawnBinary(binaryPath: string, port: number): void {
    const binDir = path.dirname(binaryPath);
    this.process = spawn(
      binaryPath,
      ["--host", "127.0.0.1", "--port", String(port)],
      {
        cwd: binDir,
        env: { ...process.env },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
  }

  private async spawnPython(
    backendPath: string,
    port: number
  ): Promise<void> {
    const pythonCmd = await this.findPython();
    if (!pythonCmd) {
      throw new Error(
        "Python 3.10+ not found. Install Python from https://python.org and ensure it is on your PATH."
      );
    }

    const hasDeps = await this.checkPythonDeps(pythonCmd, backendPath);
    if (!hasDeps) {
      throw new Error(
        `Python dependencies missing. Run: ${pythonCmd} -m pip install -r requirements.txt (in the backend directory)`
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

  private async checkPythonDeps(
    pythonCmd: string,
    backendPath: string
  ): Promise<boolean> {
    try {
      execSync(
        `${pythonCmd} -c "import uvicorn; import fastapi; import pydantic"`,
        { cwd: backendPath, timeout: 10000, encoding: "utf-8" }
      );
      return true;
    } catch {
      return false;
    }
  }

  private attachProcessHandlers(): void {
    if (!this.process) return;

    this.process.stdout?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(data.toString().trim());
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      this.lastStderr = text;
      this.outputChannel.appendLine(text);
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
        if (code !== 0 && code !== null) {
          this.outputChannel.appendLine(this.diagnoseExitCode(code));
        }
        this.scheduleRestart();
      }
    });
  }

  private diagnoseExitCode(code: number): string {
    const platform = process.platform;

    if (code === 126) {
      if (platform === "darwin") {
        return (
          "Binary cannot execute — macOS Gatekeeper may be blocking it. " +
          'Try: right-click the VS Code app → Open, or run "xattr -dr com.apple.quarantine" on the extension directory.'
        );
      }
      return "Binary cannot execute — check file permissions (chmod +x).";
    }

    if (code === 127) {
      return "Binary or a required shared library was not found.";
    }

    if (code === 137 || code === 9) {
      return "Backend was killed (out of memory or system kill signal).";
    }

    if (code === 1) {
      const stderr = this.lastStderr.toLowerCase();
      if (stderr.includes("address already in use") || stderr.includes("eaddrinuse")) {
        return "Port is already in use. Change it in Settings → SecureCode → Backend Port.";
      }
      if (stderr.includes("no module named")) {
        return "A required Python module is missing. Try reinstalling the extension.";
      }
      if (platform === "darwin" && stderr.includes("killed")) {
        return (
          'macOS Gatekeeper blocked the binary. Try: Open System Settings → Privacy & Security, and click "Allow Anyway".'
        );
      }
      if (platform === "win32" && (stderr.includes("access") || stderr.includes("virus"))) {
        return (
          "Windows Defender or SmartScreen may be blocking the binary. " +
          "Open Windows Security → Virus & threat protection → Protection history, and allow the SecureCode backend."
        );
      }
    }

    return `Backend exited with code ${code}. Check the output above for details.`;
  }

  private scheduleRestart(): void {
    if (this.disposed) return;
    if (this.restartCount >= MAX_RESTART_ATTEMPTS) {
      this.outputChannel.appendLine(
        `Backend crashed ${MAX_RESTART_ATTEMPTS} times. Not restarting.`
      );

      const errorDetail = this.buildCrashErrorMessage();
      vscode.window
        .showErrorMessage(errorDetail, "Show Output", "Troubleshoot")
        .then((action) => {
          if (action === "Show Output") {
            this.outputChannel.show();
          } else if (action === "Troubleshoot") {
            vscode.env.openExternal(
              vscode.Uri.parse(
                "https://github.com/Roxtop07/project-setup-doctor/issues"
              )
            );
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

  private buildCrashErrorMessage(): string {
    const platform = process.platform;
    const base = "SecureCode backend failed to start.";

    if (this.startMode === "binary") {
      if (platform === "darwin") {
        return (
          `${base} macOS may be blocking the binary — open System Settings → Privacy & Security and allow it.`
        );
      }
      if (platform === "win32") {
        return (
          `${base} Windows Defender may be blocking it — check Windows Security → Protection history.`
        );
      }
      if (platform === "linux") {
        return (
          `${base} Check that the binary has execute permissions and required shared libraries (ldd).`
        );
      }
    }

    if (this.startMode === "python") {
      return (
        `${base} Python backend failed — ensure Python 3.10+ is installed with uvicorn, fastapi, and pydantic.`
      );
    }

    return `${base} Check the SecureCode output channel for details.`;
  }

  private buildNoBinaryError(): string {
    const platform = process.platform;
    const arch = process.arch;

    return (
      `No backend binary found for ${platform}-${arch} and no Python fallback available. ` +
      `Install the platform-specific version of SecureCode for ${platform}-${arch}, ` +
      `or install Python 3.10+ with dependencies (pip install uvicorn fastapi pydantic).`
    );
  }

  private async findPython(): Promise<string | null> {
    const candidates =
      process.platform === "win32"
        ? ["python", "python3", "py -3"]
        : ["python3", "python"];

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
          this.outputChannel.appendLine(
            `Skipping ${cmd}: ${version} (need 3.10+)`
          );
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

  private isPortInUse(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const server = net.createServer();
      server.once("error", () => resolve(true));
      server.once("listening", () => {
        server.close(() => resolve(false));
      });
      server.listen(port, "127.0.0.1");
    });
  }

  private async waitForReady(timeoutMs: number): Promise<void> {
    const start = Date.now();
    let lastLog = start;

    while (Date.now() - start < timeoutMs) {
      if (this.disposed) return;

      if (this.process?.exitCode !== null && this.process?.exitCode !== undefined) {
        throw new Error(
          `Backend process exited immediately with code ${this.process.exitCode}.` +
            this.buildStartupHint()
        );
      }

      if (await this.isBackendRunning()) {
        this.ready = true;
        this.outputChannel.appendLine("Backend is ready.");
        return;
      }

      const now = Date.now();
      if (now - lastLog > 5000) {
        const elapsed = Math.round((now - start) / 1000);
        this.outputChannel.appendLine(
          `Still waiting for backend... (${elapsed}s elapsed)`
        );
        lastLog = now;
      }

      await new Promise((r) => setTimeout(r, 500));
    }

    throw new Error(
      `Backend failed to start within ${timeoutMs / 1000}s.` +
        this.buildStartupHint()
    );
  }

  private buildStartupHint(): string {
    const parts: string[] = [];

    if (this.lastStderr) {
      parts.push(`\nLast error: ${this.lastStderr.slice(0, 300)}`);
    }

    const platform = process.platform;
    if (this.startMode === "binary") {
      if (platform === "darwin") {
        parts.push(
          "\nTip: macOS may be blocking the binary. Open System Settings → Privacy & Security and look for a blocked app notice."
        );
      } else if (platform === "win32") {
        parts.push(
          "\nTip: Windows Defender may be blocking the binary. Check Windows Security → Virus & threat protection → Protection history."
        );
      } else if (platform === "linux") {
        parts.push(
          "\nTip: Check binary permissions and shared library availability (run ldd on the binary)."
        );
      }
    }

    parts.push("\nCheck the SecureCode output channel for full details.");
    return parts.join("");
  }
}
