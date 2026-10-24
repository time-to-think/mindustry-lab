from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMON = ROOT / "scripts/lib/common.sh"


class RuntimeSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="mindustry-runtime-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin))
        for key in ("JAVA_HOME", "MINDUSTRY_AGENT_PYTHON", "MINDUSTRY_LOCAL_ROOT"):
            self.env.pop(key, None)
        self.executable(self.bin / "uname", "printf 'Linux\\n'\n")
        for name in ("dirname", "mkdir", "cp"):
            (self.bin / name).symlink_to(shutil.which(name))

    def executable(self, path: pathlib.Path, body: str) -> pathlib.Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def shell(self, command: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", "-c", 'source "$1"; ' + command, "test", str(COMMON)],
            env=self.env, text=True, capture_output=True, timeout=10,
        )

    def python(self, name: str, version: tuple) -> pathlib.Path:
        # Run the helper's actual version predicate with a controlled version.
        bootstrap = f"import sys; sys.version_info={version!r}; exec(sys.argv[1])"
        return self.executable(
            self.bin / name,
            f'exec {shlex.quote(sys.executable)} -c {shlex.quote(bootstrap)} "$2"\n',
        )

    def jdk(self, version: int = 17, compiler: int | None = 17) -> pathlib.Path:
        home = self.root / f"jdk {version}"
        properties = f"    java.specification.version = {version}\n    java.home = {home}\n"
        self.executable(
            home / "bin/java",
            '[[ "$1" == "-XshowSettings:properties" && "$2" == "-version" ]] || exit 2\n'
            + f"printf '%s' {shlex.quote(properties)} >&2\n",
        )
        if compiler is not None:
            self.executable(home / "bin/javac", f"printf 'javac {compiler}.0.20\\n' >&2\n")
        return home

    def test_supported_python3_is_preferred(self) -> None:
        expected = self.python("python3", (3, 10, 0))
        self.python("python", (3, 13, 0))
        result = self.shell("find_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(expected))

    def test_old_python3_falls_back_to_supported_python(self) -> None:
        self.python("python3", (3, 9, 6))
        expected = self.python("python", (3, 13, 5))
        result = self.shell("find_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(expected))

    def test_only_old_pythons_raise_clear_error(self) -> None:
        self.python("python3", (3, 9, 6))
        self.python("python", (2, 7, 18))
        result = self.shell("find_python")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python 3.10+", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_python_raises_clear_error(self) -> None:
        result = self.shell("find_python")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINDUSTRY_AGENT_PYTHON", result.stderr)

    def test_python_override_with_spaces(self) -> None:
        expected = self.python("custom python", (3, 13, 5))
        self.env["MINDUSTRY_AGENT_PYTHON"] = str(expected)
        result = self.shell("find_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(expected))

    def test_relative_python_override_returns_absolute_path(self) -> None:
        expected = self.python("custom-python", (3, 13, 5))
        self.env["MINDUSTRY_AGENT_PYTHON"] = os.path.relpath(expected, ROOT)
        result = self.shell("find_python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isabs(result.stdout.strip()))
        self.assertEqual(pathlib.Path(result.stdout.strip()).resolve(), expected.resolve())

    def test_invalid_python_override_does_not_fall_back(self) -> None:
        self.env["MINDUSTRY_AGENT_PYTHON"] = str(self.python("old", (3, 9, 6)))
        self.python("python3", (3, 13, 5))
        result = self.shell("find_python")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINDUSTRY_AGENT_PYTHON", result.stderr)

    def test_missing_python_override_does_not_fall_back(self) -> None:
        self.env["MINDUSTRY_AGENT_PYTHON"] = str(self.bin / "missing")
        self.python("python3", (3, 13, 5))
        result = self.shell("find_python")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MINDUSTRY_AGENT_PYTHON", result.stderr)

    def test_broken_python_is_rejected(self) -> None:
        self.executable(self.bin / "python3", "exit 2\n")
        self.assertNotEqual(self.shell("find_python").returncode, 0)

    def test_explicit_jdk17_with_spaces_is_selected(self) -> None:
        home = self.jdk()
        self.env["JAVA_HOME"] = str(home)
        result = self.shell("find_java")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(home / "bin/java"))

    def test_explicit_wrong_java_does_not_fall_back(self) -> None:
        self.env["JAVA_HOME"] = str(self.jdk(25, 25))
        (self.bin / "java").symlink_to(self.jdk() / "bin/java")
        result = self.shell("find_java")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JAVA_HOME", result.stderr)

    def test_jre_without_compiler_is_rejected(self) -> None:
        self.env["JAVA_HOME"] = str(self.jdk(compiler=None))
        result = self.shell("find_java")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("javac", result.stderr)

    def test_javac_startup_notice_does_not_hide_supported_version(self) -> None:
        home = self.jdk()
        self.env["JAVA_HOME"] = str(home)
        self.executable(home / "bin/javac",
                        "printf 'Picked up JAVA_TOOL_OPTIONS: -Xmx128m\\njavac 17.0.20\\n' >&2\n")
        result = self.shell("find_java")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(home / "bin/java"))

    def test_mismatched_compiler_is_rejected(self) -> None:
        self.env["JAVA_HOME"] = str(self.jdk(compiler=25))
        self.assertNotEqual(self.shell("find_java").returncode, 0)

    def test_path_java_resolves_home_and_exports_to_child(self) -> None:
        home = self.jdk()
        (self.bin / "java").symlink_to(home / "bin/java")
        result = self.shell('use_java17; /bin/bash -c \'printf "%s\\n%s\\n" "$JAVA_HOME" "$(command -v java)"\'')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(home), str(home / "bin/java")])

    def test_wrong_path_java_is_rejected(self) -> None:
        (self.bin / "java").symlink_to(self.jdk(25, 25) / "bin/java")
        result = self.shell("find_java")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JDK 17", result.stderr)

    def test_missing_java_is_rejected(self) -> None:
        result = self.shell("find_java")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JDK 17", result.stderr)

    def test_build_entrypoints_export_selected_jdk_to_gradle(self) -> None:
        home = self.jdk()
        (self.bin / "java").symlink_to(home / "bin/java")
        checkout = self.root / "checkout"
        (checkout / "scripts/lib").mkdir(parents=True)
        shutil.copy(COMMON, checkout / "scripts/lib/common.sh")
        self.env["MINDUSTRY_DATA_DIR"] = str(self.root / "client data")
        self.executable(
            checkout / "gradlew",
            'printf "%s\\n%s\\n" "$JAVA_HOME" "$(command -v java)" > selected-jdk.txt\n'
            'mkdir -p build/libs\n'
            'touch build/libs/mindustry-rts-spectator.jar\n',
        )
        (self.bin / "touch").symlink_to(shutil.which("touch"))
        for name in ("build-plugin.sh", "install-client-mod.sh"):
            with self.subTest(script=name):
                shutil.copy(ROOT / "scripts" / name, checkout / "scripts" / name)
                result = subprocess.run(
                    ["/bin/bash", str(checkout / "scripts" / name)],
                    env=self.env, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((checkout / "selected-jdk.txt").read_text().splitlines(),
                                 [str(home), str(home / "bin/java")])


if __name__ == "__main__":
    unittest.main()
