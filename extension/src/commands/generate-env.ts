import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs/promises";

export function registerGenerateEnvCommand(
  context: vscode.ExtensionContext
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "secureCode.generateEnvTemplate",
      async () => {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders?.length) return;

        const rootPath = folders[0].uri.fsPath;
        const envPath = path.join(rootPath, ".env");
        const examplePath = path.join(rootPath, ".env.example");

        let vars: string[] = [];

        try {
          const envContent = await fs.readFile(envPath, "utf-8");
          vars = extractEnvVars(envContent);
        } catch {
          const srcFiles = await findSourceFiles(rootPath);
          const foundVars = new Set<string>();
          for (const file of srcFiles) {
            try {
              const content = await fs.readFile(file, "utf-8");
              for (const v of extractEnvReferences(content)) {
                foundVars.add(v);
              }
            } catch {
              // skip unreadable files
            }
          }
          vars = [...foundVars].sort();
        }

        if (vars.length === 0) {
          vscode.window.showInformationMessage(
            "No environment variables detected."
          );
          return;
        }

        const content = vars.map((v) => `${v}=`).join("\n") + "\n";

        await fs.writeFile(examplePath, content, "utf-8");
        const doc = await vscode.workspace.openTextDocument(examplePath);
        await vscode.window.showTextDocument(doc);

        vscode.window.showInformationMessage(
          `Generated .env.example with ${vars.length} variables.`
        );
      }
    )
  );
}

function extractEnvVars(content: string): string[] {
  return content
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"))
    .map((l) => l.split("=")[0].trim())
    .filter(Boolean);
}

function extractEnvReferences(content: string): string[] {
  const patterns = [
    /process\.env\.(\w+)/g,
    /os\.environ\[['"](\w+)['"]\]/g,
    /os\.environ\.get\(['"](\w+)['"]/g,
    /os\.getenv\(['"](\w+)['"]/g,
    /env\(['"](\w+)['"]\)/g,
  ];

  const vars: string[] = [];
  for (const pattern of patterns) {
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      vars.push(match[1]);
    }
  }
  return vars;
}

async function findSourceFiles(rootPath: string): Promise<string[]> {
  const results: string[] = [];
  const extensions = new Set([
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".env",
  ]);
  const excludeDirs = new Set([
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
  ]);

  async function walk(dir: string, depth: number): Promise<void> {
    if (depth > 5) return;
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (excludeDirs.has(entry.name)) continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          await walk(full, depth + 1);
        } else if (extensions.has(path.extname(entry.name))) {
          results.push(full);
        }
      }
    } catch {
      // skip inaccessible directories
    }
  }

  await walk(rootPath, 0);
  return results.slice(0, 500);
}
