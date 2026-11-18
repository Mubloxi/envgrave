# Zsh completion for EnvGrave
# Source this file in your .zshrc:
#   source /path/to/envgrave.zsh

#compdef envgrave

_envgrave() {
    local -a commands
    commands=(
        'scan:Scan a project for environment variable issues'
        'check:Scan the current directory and fail if variables are missing'
        'list:List discovered environment variables and where they are referenced'
    )

    local -a opts
    opts=(
        '--help[Show help message]'
        '--version[Show version]'
        '--json[Machine-readable JSON output]'
        '--quiet[Minimal output for CI]'
        '--strict[Treat warnings as failures]'
        '--no-color[Disable color output]'
        '--debug[Show full tracebacks on errors]'
        '--ignore:[Extra directory names to ignore]:_files'
    )

    if (( CURRENT == 2 )); then
        _describe 'command' commands
    elif (( CURRENT > 2 )); then
        _arguments '*: :_files'
    fi
}

_envgrave "$@"
