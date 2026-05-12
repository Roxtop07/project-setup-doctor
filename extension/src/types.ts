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
  | "epl"
  | "go"
  | "rust"
  | "java"
  | "kotlin"
  | "scala"
  | "ruby"
  | "php"
  | "csharp"
  | "swift"
  | "dart"
  | "elixir"
  | "c"
  | "cpp"
  | "perl"
  | "lua"
  | "haskell"
  | "clojure"
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
  has_epl_files: boolean;
  has_go_mod: boolean;
  has_cargo_toml: boolean;
  has_pom_xml: boolean;
  has_build_gradle: boolean;
  has_gemfile: boolean;
  has_composer_json: boolean;
  has_csproj: boolean;
  has_sln: boolean;
  has_package_swift: boolean;
  has_pubspec_yaml: boolean;
  has_mix_exs: boolean;
  has_makefile: boolean;
  has_cmakelists: boolean;
  has_cabal: boolean;
  has_stack_yaml: boolean;
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
