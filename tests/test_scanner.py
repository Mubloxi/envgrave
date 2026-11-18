import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from envgrave.scanner import MAX_FILE_SIZE, analyze, scan  # noqa: E402


def make_project(files):
    """Create a temp project from {relpath: content} and return its directory."""
    tmp = tempfile.mkdtemp()
    for rel, content in files.items():
        full = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(full, mode, encoding=None if mode == "wb" else "utf-8") as fh:
            fh.write(content)
    return tmp


class EnvFileParsingTests(unittest.TestCase):
    def test_simple_assignment(self):
        tmp = make_project({".env": "FOO=bar\nBAZ=qux\n"})
        result = scan(tmp)
        self.assertEqual(sorted(result.definitions), ["BAZ", "FOO"])

    def test_comments_and_blank_lines_ignored(self):
        tmp = make_project({".env": "# a comment\n\nFOO=bar\n  # indented comment\n"})
        result = scan(tmp)
        self.assertEqual(list(result.definitions), ["FOO"])

    def test_quoted_and_empty_values(self):
        tmp = make_project({".env": 'FOO="bar"\nBAZ=\'qux\'\nEMPTY=\n'})
        result = scan(tmp)
        self.assertEqual(sorted(result.definitions), ["BAZ", "EMPTY", "FOO"])

    def test_export_prefix(self):
        tmp = make_project({".env": "export FOO=bar\nBAZ=qux\n"})
        result = scan(tmp)
        self.assertEqual(sorted(result.definitions), ["BAZ", "FOO"])

    def test_duplicate_keys_in_same_file(self):
        tmp = make_project({".env": "FOO=1\nBAR=2\nFOO=3\n"})
        result = scan(tmp)
        analysis = analyze(result)
        self.assertIn("FOO", analysis.duplicates)
        self.assertEqual([d.line for d in analysis.duplicates["FOO"]], [1, 3])
        self.assertNotIn("BAR", analysis.duplicates)


class ReferenceTests(unittest.TestCase):
    def test_js_dot_access(self):
        tmp = make_project({"app.js": "const url = process.env.DATABASE_URL\n"})
        result = scan(tmp)
        self.assertEqual(list(result.references), ["DATABASE_URL"])

    def test_js_bracket_access(self):
        tmp = make_project(
            {"app.js": 'const a = process.env["API_KEY"]\nconst b = process.env[\'TOKEN\']\n'}
        )
        result = scan(tmp)
        self.assertEqual(sorted(result.references), ["API_KEY", "TOKEN"])

    def test_js_destructuring(self):
        tmp = make_project(
            {
                "app.js": "const { PORT, HOST } = process.env;\n"
                "const { DEBUG = true } = process.env;\n"
            }
        )
        result = scan(tmp)
        self.assertEqual(sorted(result.references), ["DEBUG", "HOST", "PORT"])

    def test_python_references(self):
        tmp = make_project(
            {
                "app.py": 'os.getenv("DATABASE_URL")\n'
                'api_key = os.environ["API_KEY"]\n'
                "token = os.environ.get('TOKEN')\n"
            }
        )
        result = scan(tmp)
        self.assertEqual(sorted(result.references), ["API_KEY", "DATABASE_URL", "TOKEN"])

    def test_dynamic_references_not_detected(self):
        tmp = make_project(
            {"app.js": "const key = process.env[varName]\n",
             "app.py": "value = os.getenv(name)\n"}
        )
        result = scan(tmp)
        self.assertEqual(result.references, {})

    def test_value_not_recorded(self):
        tmp = make_project({".env": "SECRET=super-secret-value\n", "app.js": "process.env.SECRET\n"})
        result = scan(tmp)
        self.assertIn("SECRET", result.definitions)
        self.assertIn("SECRET", result.references)


class DetectionTests(unittest.TestCase):
    def test_unused_variables(self):
        tmp = make_project({".env": "UNUSED=1\nUSED=2\n", "app.js": "process.env.USED\n"})
        analysis = analyze(scan(tmp))
        self.assertIn("UNUSED", analysis.unused)
        self.assertNotIn("USED", analysis.unused)

    def test_missing_variables(self):
        tmp = make_project({".env": "DEFINED=1\n", "app.js": "process.env.MISSING\n"})
        analysis = analyze(scan(tmp))
        self.assertIn("MISSING", analysis.missing)
        self.assertNotIn("DEFINED", analysis.missing)

    def test_duplicates(self):
        tmp = make_project({".env": "PORT=3000\nPORT=8000\n"})
        analysis = analyze(scan(tmp))
        self.assertIn("PORT", analysis.duplicates)

    def test_inconsistent_names(self):
        tmp = make_project({".env": "DATABSE_URL=1\nDATABASE_URL=2\nOTHER=3\n"})
        analysis = analyze(scan(tmp))
        self.assertEqual(analysis.inconsistent, [("DATABSE_URL", "DATABASE_URL")])

    def test_inconsistent_suggests_shorter_name_first(self):
        tmp = make_project({".env": "DATABASE_URL=1\nDATABSE_URL=2\n"})
        analysis = analyze(scan(tmp))
        self.assertEqual(analysis.inconsistent, [("DATABSE_URL", "DATABASE_URL")])

    def test_inconsistent_missing_suggestion(self):
        tmp = make_project({".env": "DATABASE_URL=1\n", "app.js": "process.env.DATABSE_URL\n"})
        analysis = analyze(scan(tmp))
        self.assertIn(("DATABSE_URL", "DATABASE_URL"), analysis.inconsistent)

    def test_valid_variables(self):
        tmp = make_project({".env": "A=1\nB=2\n", "app.js": "process.env.A\n"})
        analysis = analyze(scan(tmp))
        self.assertEqual(analysis.valid, ["A"])


class ProjectScanTests(unittest.TestCase):
    def test_ignored_directories(self):
        tmp = make_project(
            {
                "node_modules/dep.js": "process.env.HIDDEN\n",
                "venv/app.py": 'os.getenv("ALSO_HIDDEN")\n',
                "dist/bundle.js": "process.env.DIST_VAR\n",
                ".env": "HIDDEN=1\nVISIBLE=1\n",
                "app.js": "process.env.VISIBLE\n",
            }
        )
        result = scan(tmp)
        analysis = analyze(result)
        self.assertNotIn("HIDDEN", result.references)
        self.assertNotIn("ALSO_HIDDEN", result.references)
        self.assertNotIn("DIST_VAR", result.references)
        self.assertIn("VISIBLE", result.references)

    def test_env_file_differences(self):
        tmp = make_project({".env": "A=1\nB=2\n", ".env.example": "A=1\n"})
        analysis = analyze(scan(tmp))
        self.assertEqual(len(analysis.env_file_diffs), 1)
        self.assertEqual(analysis.env_file_diffs[0]["name"], "B")

    def test_no_env_files(self):
        tmp = make_project({"app.js": "process.env.A\n"})
        result = scan(tmp)
        self.assertEqual(result.env_files, [])

    def test_custom_ignore(self):
        tmp = make_project(
            {"custom/dep.js": "process.env.SECRET\n", ".env": "SECRET=1\n", "app.js": "process.env.VISIBLE\n"}
        )
        result = scan(tmp, ignored_dirs={"custom"})
        self.assertNotIn("SECRET", result.references)

    def test_env_ignore_file(self):
        tmp = make_project(
            {".envgraveignore": "secrets\n", "secrets/app.js": "process.env.HIDDEN\n", ".env": "HIDDEN=1\n"}
        )
        result = scan(tmp)
        self.assertNotIn("HIDDEN", result.references)

    def test_symlink_outside_not_followed(self):
        tmp = make_project({"app.js": "process.env.X\n", ".env": "X=1\n"})
        outside = tempfile.mkdtemp()
        with open(os.path.join(outside, "secret.js"), "w") as fh:
            fh.write("process.env.SECRET_OUTSIDE\n")
        try:
            os.symlink(os.path.join(outside, "secret.js"), os.path.join(tmp, "link.js"))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this system")
        result = scan(tmp)
        self.assertNotIn("SECRET_OUTSIDE", result.references)

    def test_large_file_skipped(self):
        tmp = make_project(
            {
                "big.js": "X" * (MAX_FILE_SIZE + 1),
                ".env": "BIG=1\n",
                "app.js": "process.env.BIG\n",
            }
        )
        result = scan(tmp)
        self.assertEqual(result.skipped_files, 1)
        self.assertIn("BIG", result.references)

    def test_invalid_utf8_file_does_not_crash(self):
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "weird.js"), "wb") as fh:
            fh.write(b"\xff\xfe\x00process.env.Y\n")
        with open(os.path.join(tmp, ".env"), "w", encoding="utf-8") as fh:
            fh.write("Y=1\n")
        result = scan(tmp)
        self.assertNotIn("Y", result.references)

    def test_scan_subdir(self):
        tmp = make_project({"sub/app.js": "process.env.PORT\n", ".env": "PORT=3000\n"})
        result = scan(os.path.join(tmp, "sub"))
        self.assertIn("PORT", result.references)

    def test_files_scanned_count(self):
        tmp = make_project({"a.js": "process.env.A\n", "b.py": 'os.getenv("B")\n', ".env": "A=1\nB=2\n"})
        result = scan(tmp)
        self.assertEqual(result.files_scanned, 2)


class CliTests(unittest.TestCase):
    def run_cli(self, args, cwd=None):
        return subprocess.run(
            [sys.executable, "-m", "envgrave"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    def test_version(self):
        proc = self.run_cli(["--version"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.0.0", proc.stdout)

    def test_help(self):
        proc = self.run_cli(["--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("scan", proc.stdout)

    def test_no_args_scans_current_directory(self):
        tmp = make_project({".env": "A=1\n", "app.js": "process.env.A\n"})
        proc = self.run_cli([], cwd=tmp)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 files scanned", proc.stdout)

    def test_scan_path(self):
        tmp = make_project({".env": "A=1\n", "app.js": "process.env.A\n"})
        proc = self.run_cli(["scan", tmp])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Valid (1)", proc.stdout)

    def test_json_output(self):
        tmp = make_project({".env": "UNUSED=1\n", "app.js": "process.env.MISSING\n"})
        proc = self.run_cli(["scan", tmp, "--json"])
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["summary"]["unused"], 1)
        self.assertEqual(data["summary"]["missing"], 1)
        self.assertEqual(data["files_scanned"], 1)

    def test_check_exits_nonzero_when_missing(self):
        tmp = make_project({"app.js": "process.env.MISSING\n"})
        proc = self.run_cli(["check"], cwd=tmp)
        self.assertNotEqual(proc.returncode, 0)

    def test_check_exits_zero_when_present(self):
        tmp = make_project({".env": "X=1\n", "app.js": "process.env.X\n"})
        proc = self.run_cli(["check"], cwd=tmp)
        self.assertEqual(proc.returncode, 0)

    def test_strict_exits_nonzero_on_warnings(self):
        tmp = make_project({".env": "UNUSED=1\n"})
        proc = self.run_cli(["--strict", "scan", tmp])
        self.assertNotEqual(proc.returncode, 0)

    def test_quiet_output(self):
        tmp = make_project({".env": "A=1\n", "app.js": "process.env.A\n"})
        proc = self.run_cli(["scan", tmp, "--quiet"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 valid", proc.stdout)
        self.assertNotIn("Valid", proc.stdout)

    def test_list_command(self):
        tmp = make_project({".env": "A=1\nB=2\n", "app.js": "process.env.A\nprocess.env.MISSING\n"})
        proc = self.run_cli(["list"], cwd=tmp)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("A", proc.stdout)
        self.assertIn("MISSING", proc.stdout)

    def test_ignore_option(self):
        tmp = make_project(
            {"custom/dep.js": "process.env.SECRET\n", ".env": "SECRET=1\nVISIBLE=1\n", "app.js": "process.env.VISIBLE\n"}
        )
        proc = self.run_cli(["scan", tmp, "--ignore", "custom"])
        # custom/dep.js is ignored, so SECRET is no longer referenced
        self.assertIn("Unused (1)", proc.stdout)
        self.assertIn("SECRET", proc.stdout)
        self.assertNotIn("Missing", proc.stdout)


if __name__ == "__main__":
    unittest.main()
