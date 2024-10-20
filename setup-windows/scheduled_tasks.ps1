# -------- Run with PowerShell (as Administrator) --------

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


# -------- Scheduled Tasks (Daily) --------

# https://stackoverflow.com/questions/54061724/run-a-script-as-hidden-scheduled-task-with-powershell
# https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType "S4U" -RunLevel "Highest"
# https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset
$settings = New-ScheduledTaskSettingsSet -Hidden


# --- Provision System ---

$taskName = "CRON PC Setup"
$action = New-ScheduledTaskAction -Execute "pwsh" -Argument "-NonInteractive -File F:\Repos\pc-env\powershell\pc_setup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00am"
# $taskExists = Get-ScheduledTask | Where-Object { $_.TaskName -like $taskName }
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (!$taskExists)
{
    Write-Output "Scheduled task '$taskName' does not exist, creating..."
    # https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
}
else
{
    Write-Output "Scheduled task '$taskName' was found, updating..."
    # https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/set-scheduledtask
    Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings
}


# --- Backup System ---

# Get the Python install directory from the executable path
$pythonExecutablePath = python -c "import sys; print(sys.executable)"
$pythonInstallLocation = Split-Path -Path $pythonExecutablePath -Parent
Write-Output "Python install location: $pythonInstallLocation"

$taskName = "CRON PC Clean"
# $py_exe = "C:\Python312\python.exe"
$py_exe = "${pythonInstallLocation}\python.exe"
$py_script = "$Env:AppData\Python\bin\pc_clean.py"
$action = New-ScheduledTaskAction -Execute $py_exe -Argument $py_script
$trigger = New-ScheduledTaskTrigger -Daily -At "04:00am"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (!$taskExists)
{
    Write-Output "Scheduled task '$taskName' does not exist, creating..."
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
}
else
{
    Write-Output "Scheduled task '$taskName' was found, updating..."
    Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings
}


# Write-Output "--- Completed Scheduled Tasks ---"
Write-ColorOutput green "--- Completed Scheduled Tasks ---"
