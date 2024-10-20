# -------- Run with PowerShell (as Administrator) --------

# $Env:PSModulePath     path for PowerShell modules (Import-Module)
# $PSHome               path of main PowerShell install
# Get-Module -ListAvailable
# Install-Module <module-name>
# Import-Module <module-name>

# . $PSScriptRoot\ConsoleMode.ps1
# . $PSScriptRoot\Utils.ps1

# Import-Module F:\Repos\pc-env\powershell\boilerplate.psm1


# --- PowerShell Gallery: publish to / install from  ---
# Register-PSRepository -Name 'myRepositoryName' -SourceLocation 'C:\MyExampleFolder'
# Register-PSRepository -Name 'pc-env' -SourceLocation 'E:\Repos\pc-env\powershell' -InstallationPolicy Trusted
# Install-Module 'Some-Module' -Repository 'myRepositoryName'
# Install-Module 'boilerplate' -Repository 'pc-env'


# https://stackoverflow.com/questions/4647756/is-there-a-way-to-specify-a-font-color-when-using-write-output
function Write-ColorOutput($ForegroundColor)
{
    # Save the current color
    $fc = [Console]::ForegroundColor

    # Set the new color
    [Console]::ForegroundColor = $ForegroundColor

    # Output
    if ($args)
    {
        Write-Output $args
    }
    else
    {
        $input | Write-Output
    }

    # Restore the original color
    [Console]::ForegroundColor = $fc
}


$exportModuleMemberParams = @{
    Function = @(
        'Write-ColorOutput'
    )
    # Variable = @(
    #     'GitPromptScriptBlock'
    # )
}

Export-ModuleMember @exportModuleMemberParams
