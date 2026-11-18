# PowerShell completion for EnvGrave
# Add to your Microsoft.PowerShell_profile.ps1:
#   Import-Module /path/to/envgrave.ps1

Register-ArgumentCompleter -Native -CommandName 'envgrave' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $completions = @(
        'scan', 'check', 'list',
        '--help', '--version', '--json', '--quiet', '--strict',
        '--no-color', '--debug', '--ignore'
    )

    $completions | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
