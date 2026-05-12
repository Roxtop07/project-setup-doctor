from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess

from models.contracts import ProjectInfo, ProjectType


class ProjectDetector:
    def __init__(self, root_path: str):
        self.root = root_path

    def detect(self) -> ProjectInfo:
        name = os.path.basename(os.path.abspath(self.root))
        types: list[ProjectType] = []
        frameworks: list[str] = []

        has_pkg = os.path.isfile(self._p("package.json"))
        has_req = os.path.isfile(self._p("requirements.txt"))
        has_pyproject = os.path.isfile(self._p("pyproject.toml"))
        has_dockerfile = os.path.isfile(self._p("Dockerfile"))
        has_compose = any(
            os.path.isfile(self._p(f))
            for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        )
        has_epl = bool(
            glob.glob(os.path.join(self.root, "*.epl"))
            or glob.glob(os.path.join(self.root, "*", "*.epl"))
        )
        has_go_mod = os.path.isfile(self._p("go.mod"))
        has_cargo_toml = os.path.isfile(self._p("Cargo.toml"))
        has_pom_xml = os.path.isfile(self._p("pom.xml"))
        has_build_gradle = os.path.isfile(self._p("build.gradle")) or os.path.isfile(self._p("build.gradle.kts"))
        has_gemfile = os.path.isfile(self._p("Gemfile"))
        has_composer_json = os.path.isfile(self._p("composer.json"))
        has_csproj = bool(glob.glob(os.path.join(self.root, "*.csproj")))
        has_sln = bool(glob.glob(os.path.join(self.root, "*.sln")))
        has_package_swift = os.path.isfile(self._p("Package.swift"))
        has_pubspec_yaml = os.path.isfile(self._p("pubspec.yaml"))
        has_mix_exs = os.path.isfile(self._p("mix.exs"))
        has_makefile = os.path.isfile(self._p("Makefile")) or os.path.isfile(self._p("makefile"))
        has_cmakelists = os.path.isfile(self._p("CMakeLists.txt"))
        has_cabal = bool(glob.glob(os.path.join(self.root, "*.cabal")))
        has_stack_yaml = os.path.isfile(self._p("stack.yaml"))

        has_env = os.path.isfile(self._p(".env"))
        has_env_example = os.path.isfile(self._p(".env.example"))
        has_readme = any(
            os.path.isfile(self._p(f))
            for f in ["README.md", "README.rst", "README.txt", "README"]
        )
        has_gitignore = os.path.isfile(self._p(".gitignore"))

        if has_pkg:
            pkg_types, pkg_frameworks = self._detect_node_project()
            types.extend(pkg_types)
            frameworks.extend(pkg_frameworks)

        if has_req or has_pyproject:
            py_types, py_frameworks = self._detect_python_project()
            types.extend(py_types)
            frameworks.extend(py_frameworks)

        if has_epl:
            epl_types, epl_frameworks = self._detect_epl_project()
            types.extend(epl_types)
            frameworks.extend(epl_frameworks)

        if has_go_mod:
            go_types, go_frameworks = self._detect_go_project()
            types.extend(go_types)
            frameworks.extend(go_frameworks)

        if has_cargo_toml:
            rs_types, rs_frameworks = self._detect_rust_project()
            types.extend(rs_types)
            frameworks.extend(rs_frameworks)

        if has_pom_xml or has_build_gradle:
            jvm_types, jvm_frameworks = self._detect_jvm_project()
            types.extend(jvm_types)
            frameworks.extend(jvm_frameworks)

        if has_gemfile:
            rb_types, rb_frameworks = self._detect_ruby_project()
            types.extend(rb_types)
            frameworks.extend(rb_frameworks)

        if has_composer_json:
            php_types, php_frameworks = self._detect_php_project()
            types.extend(php_types)
            frameworks.extend(php_frameworks)

        if has_csproj or has_sln:
            cs_types, cs_frameworks = self._detect_csharp_project()
            types.extend(cs_types)
            frameworks.extend(cs_frameworks)

        if has_package_swift:
            swift_types, swift_frameworks = self._detect_swift_project()
            types.extend(swift_types)
            frameworks.extend(swift_frameworks)

        if has_pubspec_yaml:
            dart_types, dart_frameworks = self._detect_dart_project()
            types.extend(dart_types)
            frameworks.extend(dart_frameworks)

        if has_mix_exs:
            ex_types, ex_frameworks = self._detect_elixir_project()
            types.extend(ex_types)
            frameworks.extend(ex_frameworks)

        if has_cmakelists or (has_makefile and not types):
            c_types, c_frameworks = self._detect_c_cpp_project()
            types.extend(c_types)
            frameworks.extend(c_frameworks)

        if has_cabal or has_stack_yaml:
            types.append(ProjectType.HASKELL)
            frameworks.append("Haskell")

        if os.path.isfile(self._p("project.clj")) or os.path.isfile(self._p("deps.edn")):
            types.append(ProjectType.CLOJURE)
            frameworks.append("Clojure")

        if self._has_files_with_ext(".pl") or self._has_files_with_ext(".pm"):
            if not any(t in types for t in [ProjectType.PERL]):
                if os.path.isfile(self._p("cpanfile")) or os.path.isfile(self._p("Makefile.PL")):
                    types.append(ProjectType.PERL)
                    frameworks.append("Perl")

        if os.path.isfile(self._p("rockspec")) or self._has_files_with_ext(".rockspec"):
            types.append(ProjectType.LUA)
            frameworks.append("Lua")

        if has_dockerfile:
            types.append(ProjectType.DOCKER)

        if not types:
            types.append(ProjectType.UNKNOWN)

        versions = self._detect_runtime_versions()

        return ProjectInfo(
            types=list(dict.fromkeys(types)),
            root_path=self.root,
            name=name,
            has_package_json=has_pkg,
            has_requirements_txt=has_req,
            has_pyproject_toml=has_pyproject,
            has_dockerfile=has_dockerfile,
            has_docker_compose=has_compose,
            has_env_file=has_env,
            has_env_example=has_env_example,
            has_readme=has_readme,
            has_gitignore=has_gitignore,
            has_epl_files=has_epl,
            has_go_mod=has_go_mod,
            has_cargo_toml=has_cargo_toml,
            has_pom_xml=has_pom_xml,
            has_build_gradle=has_build_gradle,
            has_gemfile=has_gemfile,
            has_composer_json=has_composer_json,
            has_csproj=has_csproj,
            has_sln=has_sln,
            has_package_swift=has_package_swift,
            has_pubspec_yaml=has_pubspec_yaml,
            has_mix_exs=has_mix_exs,
            has_makefile=has_makefile,
            has_cmakelists=has_cmakelists,
            has_cabal=has_cabal,
            has_stack_yaml=has_stack_yaml,
            detected_frameworks=list(dict.fromkeys(frameworks)),
            runtime_versions=versions,
        )

    # -- Node / JavaScript / TypeScript ---------------------------------

    def _detect_node_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        try:
            pkg_path = self._p("package.json")
            if os.path.getsize(pkg_path) > 5_000_000:
                types.append(ProjectType.NODEJS)
                return types, frameworks
            with open(pkg_path) as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError):
            types.append(ProjectType.NODEJS)
            return types, frameworks

        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }

        if "next" in all_deps:
            types.append(ProjectType.NEXTJS)
            frameworks.append("Next.js")
        if "react" in all_deps:
            types.append(ProjectType.REACT)
            frameworks.append("React")
        if "express" in all_deps:
            types.append(ProjectType.EXPRESS)
            frameworks.append("Express")
        if "vue" in all_deps:
            frameworks.append("Vue.js")
        if "svelte" in all_deps or "svelte-kit" in all_deps:
            frameworks.append("Svelte")
        if "@angular/core" in all_deps:
            frameworks.append("Angular")
        if "vite" in all_deps:
            frameworks.append("Vite")

        if not types:
            types.append(ProjectType.NODEJS)

        return types, frameworks

    # -- Python ---------------------------------------------------------

    def _detect_python_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        deps_text = ""
        for fname in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
            p = self._p(fname)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "fastapi" in deps_text:
            types.append(ProjectType.FASTAPI)
            frameworks.append("FastAPI")
        if "flask" in deps_text:
            types.append(ProjectType.FLASK)
            frameworks.append("Flask")
        if "django" in deps_text:
            types.append(ProjectType.DJANGO)
            frameworks.append("Django")

        if not types:
            types.append(ProjectType.PYTHON)

        if "eplang" in deps_text:
            frameworks.append("EPL")
        if "celery" in deps_text:
            frameworks.append("Celery")
        if "sqlalchemy" in deps_text:
            frameworks.append("SQLAlchemy")
        if "pytest" in deps_text:
            frameworks.append("pytest")

        return types, frameworks

    # -- EPL ------------------------------------------------------------

    def _detect_epl_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.EPL]
        frameworks: list[str] = ["EPL"]

        deps_text = ""
        for fname in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
            p = self._p(fname)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "eplang" in deps_text:
            frameworks.append("eplang")

        return types, frameworks

    # -- Go -------------------------------------------------------------

    def _detect_go_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.GO]
        frameworks: list[str] = []

        go_mod_path = self._p("go.mod")
        try:
            with open(go_mod_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "gin-gonic/gin" in content:
            frameworks.append("Gin")
        if "gofiber/fiber" in content:
            frameworks.append("Fiber")
        if "gorilla/mux" in content:
            frameworks.append("Gorilla Mux")
        if "labstack/echo" in content:
            frameworks.append("Echo")
        if "go-chi/chi" in content:
            frameworks.append("Chi")
        if "gorm.io/gorm" in content:
            frameworks.append("GORM")
        if "cobra" in content:
            frameworks.append("Cobra")

        return types, frameworks

    # -- Rust -----------------------------------------------------------

    def _detect_rust_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.RUST]
        frameworks: list[str] = []

        cargo_path = self._p("Cargo.toml")
        try:
            with open(cargo_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "actix" in content:
            frameworks.append("Actix")
        if "tokio" in content:
            frameworks.append("Tokio")
        if "rocket" in content:
            frameworks.append("Rocket")
        if "axum" in content:
            frameworks.append("Axum")
        if "serde" in content:
            frameworks.append("Serde")
        if "diesel" in content:
            frameworks.append("Diesel")
        if "clap" in content:
            frameworks.append("Clap")

        return types, frameworks

    # -- JVM: Java / Kotlin / Scala ------------------------------------

    def _detect_jvm_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        deps_text = ""
        pom_path = self._p("pom.xml")
        if os.path.isfile(pom_path):
            try:
                with open(pom_path) as f:
                    deps_text += f.read().lower() + "\n"
            except OSError:
                pass

        for gf in ["build.gradle", "build.gradle.kts"]:
            p = self._p(gf)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "kotlin" in deps_text or os.path.isfile(self._p("build.gradle.kts")):
            types.append(ProjectType.KOTLIN)
            frameworks.append("Kotlin")
        if "scala" in deps_text:
            types.append(ProjectType.SCALA)
            frameworks.append("Scala")

        if not types:
            types.append(ProjectType.JAVA)

        if "spring" in deps_text:
            frameworks.append("Spring")
        if "quarkus" in deps_text:
            frameworks.append("Quarkus")
        if "micronaut" in deps_text:
            frameworks.append("Micronaut")
        if "ktor" in deps_text:
            frameworks.append("Ktor")
        if "hibernate" in deps_text:
            frameworks.append("Hibernate")
        if "junit" in deps_text:
            frameworks.append("JUnit")
        if "android" in deps_text:
            frameworks.append("Android")

        return types, frameworks

    # -- Ruby -----------------------------------------------------------

    def _detect_ruby_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.RUBY]
        frameworks: list[str] = []

        gemfile_path = self._p("Gemfile")
        try:
            with open(gemfile_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "rails" in content:
            frameworks.append("Rails")
        if "sinatra" in content:
            frameworks.append("Sinatra")
        if "hanami" in content:
            frameworks.append("Hanami")
        if "rspec" in content:
            frameworks.append("RSpec")
        if "sidekiq" in content:
            frameworks.append("Sidekiq")
        if "jekyll" in content:
            frameworks.append("Jekyll")

        return types, frameworks

    # -- PHP ------------------------------------------------------------

    def _detect_php_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.PHP]
        frameworks: list[str] = []

        composer_path = self._p("composer.json")
        try:
            with open(composer_path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return types, frameworks

        all_deps = {
            **data.get("require", {}),
            **data.get("require-dev", {}),
        }
        deps_str = " ".join(all_deps.keys()).lower()

        if "laravel/framework" in deps_str:
            frameworks.append("Laravel")
        if "symfony/" in deps_str:
            frameworks.append("Symfony")
        if "slim/slim" in deps_str:
            frameworks.append("Slim")
        if "wordpress" in deps_str:
            frameworks.append("WordPress")
        if "phpunit" in deps_str:
            frameworks.append("PHPUnit")

        return types, frameworks

    # -- C# / .NET ------------------------------------------------------

    def _detect_csharp_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.CSHARP]
        frameworks: list[str] = []

        deps_text = ""
        for pattern in ["*.csproj", "*.sln"]:
            for fpath in glob.glob(os.path.join(self.root, pattern)):
                try:
                    with open(fpath) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "aspnetcore" in deps_text or "microsoft.aspnetcore" in deps_text:
            frameworks.append("ASP.NET Core")
        if "xamarin" in deps_text:
            frameworks.append("Xamarin")
        if "maui" in deps_text:
            frameworks.append("MAUI")
        if "entityframework" in deps_text:
            frameworks.append("Entity Framework")
        if "xunit" in deps_text or "nunit" in deps_text:
            frameworks.append("xUnit/NUnit")
        if "blazor" in deps_text:
            frameworks.append("Blazor")

        return types, frameworks

    # -- Swift ----------------------------------------------------------

    def _detect_swift_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.SWIFT]
        frameworks: list[str] = []

        pkg_path = self._p("Package.swift")
        try:
            with open(pkg_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "vapor" in content:
            frameworks.append("Vapor")
        if "swiftui" in content:
            frameworks.append("SwiftUI")
        if "combine" in content:
            frameworks.append("Combine")

        return types, frameworks

    # -- Dart / Flutter -------------------------------------------------

    def _detect_dart_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.DART]
        frameworks: list[str] = []

        pubspec_path = self._p("pubspec.yaml")
        try:
            with open(pubspec_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "flutter" in content:
            frameworks.append("Flutter")
        if "riverpod" in content:
            frameworks.append("Riverpod")
        if "bloc" in content:
            frameworks.append("BLoC")

        return types, frameworks

    # -- Elixir ---------------------------------------------------------

    def _detect_elixir_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = [ProjectType.ELIXIR]
        frameworks: list[str] = []

        mix_path = self._p("mix.exs")
        try:
            with open(mix_path) as f:
                content = f.read().lower()
        except OSError:
            return types, frameworks

        if "phoenix" in content:
            frameworks.append("Phoenix")
        if "ecto" in content:
            frameworks.append("Ecto")
        if "nerves" in content:
            frameworks.append("Nerves")

        return types, frameworks

    # -- C / C++ --------------------------------------------------------

    def _detect_c_cpp_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        has_cpp_files = bool(
            glob.glob(os.path.join(self.root, "*.cpp"))
            or glob.glob(os.path.join(self.root, "*.cc"))
            or glob.glob(os.path.join(self.root, "*.cxx"))
            or glob.glob(os.path.join(self.root, "src", "*.cpp"))
            or glob.glob(os.path.join(self.root, "src", "*.cc"))
        )
        has_c_files = bool(
            glob.glob(os.path.join(self.root, "*.c"))
            or glob.glob(os.path.join(self.root, "src", "*.c"))
        )

        if has_cpp_files:
            types.append(ProjectType.CPP)
        if has_c_files and not has_cpp_files:
            types.append(ProjectType.C)

        if not types and os.path.isfile(self._p("CMakeLists.txt")):
            types.append(ProjectType.CPP)

        if os.path.isfile(self._p("CMakeLists.txt")):
            frameworks.append("CMake")
        if os.path.isfile(self._p("meson.build")):
            frameworks.append("Meson")
        if os.path.isfile(self._p("conanfile.txt")) or os.path.isfile(self._p("conanfile.py")):
            frameworks.append("Conan")
        if os.path.isfile(self._p("vcpkg.json")):
            frameworks.append("vcpkg")

        return types, frameworks

    # -- Runtime version detection --------------------------------------

    def _detect_runtime_versions(self) -> dict[str, str | None]:
        versions: dict[str, str | None] = {}

        for cmd, key in [
            (["node", "--version"], "node"),
            (["npm", "--version"], "npm"),
            (["python3", "--version"], "python"),
            (["pip3", "--version"], "pip"),
            (["docker", "--version"], "docker"),
            (["epl", "--version"], "epl"),
            (["go", "version"], "go"),
            (["rustc", "--version"], "rust"),
            (["cargo", "--version"], "cargo"),
            (["java", "--version"], "java"),
            (["ruby", "--version"], "ruby"),
            (["php", "--version"], "php"),
            (["dotnet", "--version"], "dotnet"),
            (["swift", "--version"], "swift"),
            (["dart", "--version"], "dart"),
            (["elixir", "--version"], "elixir"),
            (["gcc", "--version"], "gcc"),
            (["g++", "--version"], "g++"),
            (["perl", "--version"], "perl"),
        ]:
            if not shutil.which(cmd[0]):
                versions[key] = None
                continue
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                out = result.stdout.strip() or result.stderr.strip()
                versions[key] = out.split()[-1] if result.returncode == 0 and out else None
            except (subprocess.TimeoutExpired, OSError):
                versions[key] = None

        return versions

    # -- Helpers --------------------------------------------------------

    def _has_files_with_ext(self, ext: str) -> bool:
        return bool(glob.glob(os.path.join(self.root, f"*{ext}")))

    def _p(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)
