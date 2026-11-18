# EnvGrave

EnvGrave scans your project for environment variable problems — unused, missing,
duplicated, or inconsistently named variables — across `.env` files and your
source code. It reports variable names, file paths, and line numbers only. It
never reads variable values, never modifies files, and never sends anything over
the network.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/<your-username>/envgrave.git
```

Or clone and install locally:

```bash
git clone https://github.com/<your-username>/envgrave.git
cd envgrave
pip install .
```

`pip install envgrave` will be available once the package is published to PyPI.

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

## Limitations

- Only static environment variable references are detected.
- Variable values are never read or displayed.
- No network access, no telemetry, no database.

## Security

EnvGrave only reads file names, paths, and line numbers. It never displays
environment variable values, never modifies `.env` files, never executes code
from scanned projects, and never follows symlinks outside the selected project.
Directories such as `.git`, `node_modules`, `venv`, `dist`, and `build` are
ignored by default, and files larger than 1 MB are skipped.

## Contributing

Bug reports and pull requests are welcome. Run the tests with:

```bash
python -m unittest discover -s tests -t .
```

## License

[MIT](LICENSE)
