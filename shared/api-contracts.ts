export type Severity = "error" | "warning" | "info";

export type ProjectType =
  | "nextjs"
  | "react"
  | "nodejs"
  | "express"
  | "fastapi"
  | "flask"
  | "django"
  | "python"
  | "docker"
  | "unknown";

export interface ProjectInfo {
  types: ProjectType[];
  rootPath: string;
  name: string;
  hasPackageJson: boolean;
  hasRequirementsTxt: boolean;
  hasPyprojectToml: boolean;
  hasDockerfile: boolean;
  hasDockerCompose: boolean;
  hasEnvFile: boolean;
  hasEnvExample: boolean;
  hasReadme: boolean;
  hasGitIgnore: boolean;
  detectedFrameworks: string[];
  runtimeVersions: Record<string, string | null>;
}

export interface Issue {
  id: string;
  analyzer: string;
  severity: Severity;
  message: string;
  file?: string;
  line?: number;
  fix?: AutoFix;
}

export interface AutoFix {
  id: string;
  description: string;
  command?: string;
  fileCreate?: { path: string; content: string };
  fileEdit?: { path: string; search: string; replace: string };
}

export interface ScoreBreakdown {
  dependencyHygiene: number;
  docsQuality: number;
  setupReadiness: number;
  security: number;
  environmentCompleteness: number;
}

export interface HealthScore {
  total: number;
  breakdown: ScoreBreakdown;
  grade: "A" | "B" | "C" | "D" | "F";
}

export interface ScanRequest {
  rootPath: string;
  analyzers?: string[];
  incremental?: boolean;
}

export interface ScanResult {
  projectInfo: ProjectInfo;
  issues: Issue[];
  healthScore: HealthScore;
  scanDurationMs: number;
  timestamp: string;
}

export interface AutoFixRequest {
  rootPath: string;
  fixIds: string[];
}

export interface AutoFixResult {
  applied: string[];
  failed: { id: string; error: string }[];
}

export interface BackendStatus {
  status: "ok";
  version: string;
  analyzers: string[];
}
