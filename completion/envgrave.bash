# Bash completion for EnvGrave
# Source this file in your .bashrc or .bash_profile:
#   source /path/to/envgrave.bash

_envgrave_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="scan check list --help --version --json --quiet --strict --no-color --debug --ignore"

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    case "${prev}" in
        scan|check|list)
            COMPREPLY=( $(compgen -f -- ${cur}) )
            return 0
            ;;
        --ignore)
            COMPREPLY=( $(compgen -f -- ${cur}) )
            return 0
            ;;
        *)
            COMPREPLY=( $(compgen -W "scan check list" -- ${cur}) )
            return 0
            ;;
    esac
}

complete -F _envgrave_completion envgrave
