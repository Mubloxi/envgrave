# EnvGrave

EnvGrave scans your project for environment variable problems — unused, missing,
duplicated, or inconsistently named variables — across `.env` files and your
source code. It reports variable names, file paths, and line numbers only. It
never reads variable values, never modifies files, and never sends anything over
the network.

## Installation

### Python (pip, pipx, uv)

```bash
pip install envgrave
```

Also works with pipx and uv:

```bash
pipx install envgrave
uv tool install envgrave
uvx envgrave scan .
```

### From GitHub

```bash
pip install git+https://github.com/Mubloxi/envgrave.git
```

Or clone and install locally:

```bash
git clone https://github.com/Mubloxi/envgrave.git
cd envgrave
pip install .
```

### Windows — standalone executable

Download `envgrave-1.0.0-windows-x64.zip` from
[GitHub Releases](https://github.com/Mubloxi/envgrave/releases). Extract it and
run `envgrave.exe` from any directory. No Python installation required.

Optional: add the extracted folder to your PATH so you can run `envgrave` from
anywhere.

### Linux — standalone executable

Download `envgrave-1.0.0-linux-x64.tar.gz` or
`envgrave-1.0.0-linux-arm64.tar.gz` from GitHub Releases. Extract and run the
`envgrave` binary.

### macOS — standalone executable

Download `envgrave-1.0.0-macos-x64.tar.gz` or
`envgrave-1.0.0-macos-arm64.tar.gz` from GitHub Releases. Extract and run the
`envgrave` binary.

### Linux packages

**Debian/Ubuntu (.deb):**

```bash
sudo dpkg -i envgrave_1.0.0_amd64.deb
```

Uninstall:

```bash
sudo apt remove envgrave
```

**Fedora/RPM (.rpm):**

```bash
sudo rpm -i envgrave-1.0.0-1.noarch.rpm
```

Uninstall:

```bash
sudo rpm -e envgrave
```

### Package managers

**WinGet** (Windows):

```bash
winget install Mubloxi.EnvGrave
```

**Homebrew** (macOS/Linux):

```bash
brew install envgrave
```

Only documented methods that have been built and published are listed above.

## Quick start

```bash
# Scan the current directory
envgrave

# Scan another project
envgrave scan ./my-project

# Exit nonzero if required variables are missing (useful in CI)
envgrave check

# List every discovered variable and where it is referenced
envgrave list
```

`envgrave` with no arguments scans the current directory, same as `envgrave scan .`.

## Options

```
--json        Machine-readable JSON output
--quiet       Minimal output for CI pipelines
--no-color    Disable terminal colors
--strict      Treat warnings as failures (nonzero exit code)
--ignore      Extra directory names to ignore, comma-separated
--debug       Show full tracebacks on unexpected errors
--version     Show version and exit
```

Colors are disabled automatically when output is redirected or `NO_COLOR` is set.

## Example output

```
$ envgrave scan .

EnvGrave v1.0.0

Scanning ....
42 files scanned

Unused (2)
  OLD_API_KEY   .env:3
  DEBUG_TOKEN   .env:7

Missing (1)
  REDIS_URL     src/database.js:18

Duplicates (1)
  PORT          .env:4, .env:12

Valid (3)
  DATABASE_URL
  SESSION_SECRET
  NODE_ENV

Summary
  3 valid · 2 unused · 1 missing · 1 duplicate
```

## Supported languages

JavaScript, TypeScript, Python, and Node.js. Statically detectable patterns:

```javascript
process.env.DATABASE_URL
process.env["API_KEY"]
const { PORT } = process.env;
```

```python
os.getenv("DATABASE_URL")
os.environ["API_KEY"]
os.environ.get("API_KEY")
```

Dynamic references like `process.env[varName]` cannot be determined statically
and are intentionally ignored.

## Env files

`.env`, `.env.local`, `.env.example`, `.env.production`, and `.env.development`
are parsed when present. Differences between them are reported as information,
not errors, since different files intentionally contain different variables.

A `.envgraveignore` file with one directory or file name per line excludes
entries from the scan.

## Shell completion

Bash, Zsh, and PowerShell completion scripts are in the `completion/` directory.
Source the appropriate file in your shell profile.

## Limitations

- Only static environment variable references are detected.
- Variable values are never read or displayed.
- No network access, no telemetry, no database.
- Standalone executables bundle a Python interpreter and are larger than the pip package.

## Security

EnvGrave only reads file names, paths, and line numbers. It never displays
environment variable values, never modifies `.env` files, never executes code
from scanned projects, and never follows symlinks outside the selected project.
Directories such as `.git`, `node_modules`, `venv`, `dist`, and `build` are
ignored by default, and files larger than 1 MB are skipped.

## Updates and uninstallation

**pip:** `pip install --upgrade envgrave` / `pip uninstall envgrave`

**pipx:** `pipx upgrade envgrave` / `pipx uninstall envgrave`

**uv:** `uv tool upgrade envgrave` / `uv tool uninstall envgrave`

**Standalone executable:** Replace the binary with the new version. No registry
changes, services, or scheduled tasks are created.

**.deb:** `sudo apt remove envgrave`

**.rpm:** `sudo rpm -e envgrave`

**Homebrew:** `brew upgrade envgrave` / `brew uninstall envgrave`

## Contributing

Bug reports and pull requests are welcome. Run the tests with:

```bash
python -m unittest discover -s tests -t .
```

## License

[MIT](LICENSE)
