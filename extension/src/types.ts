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
  root_path: string;
  name: string;
  has_package_json: boolean;
  has_requirements_txt: boolean;
  has_pyproject_toml: boolean;
  has_dockerfile: boolean;
  has_docker_compose: boolean;
  has_env_file: boolean;
  has_env_example: boolean;
  has_readme: boolean;
  has_gitignore: boolean;
  detected_frameworks: string[];
  runtime_versions: Record<string, string | null>;
}

export interface AutoFix {
  id: string;
  description: string;
  command?: string;
  file_create?: { path: string; content: string };
  file_edit?: { path: string; search: string; replace: string };
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

export interface ScoreBreakdown {
  dependency_hygiene: number;
  docs_quality: number;
  setup_readiness: number;
  security: number;
  environment_completeness: number;
}

export interface HealthScore {
  total: number;
  breakdown: ScoreBreakdown;
  grade: "A" | "B" | "C" | "D" | "F";
}

export interface ScanResult {
  project_info: ProjectInfo;
  issues: Issue[];
  health_score: HealthScore;
  scan_duration_ms: number;
  timestamp: string;
}

export interface AutoFixResult {
  applied: string[];
  failed: { id: string; error: string }[];
}

export interface BackendStatus {
  status: string;
  version: string;
  analyzers: string[];
}
