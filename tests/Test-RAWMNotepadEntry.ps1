# Exercises the installed roman command. -Approve opens and leaves one new Notepad draft visible.
[CmdletBinding()]
param([switch]$Approve)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fixture=Join-Path $PSScriptRoot ('.runs\notepad-entry-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
$draftFolder=Join-Path $root 'data\agent\drafts'
function Get-DraftPaths {
    if (Test-Path -LiteralPath $draftFolder) {
        Get-ChildItem -LiteralPath $draftFolder -Filter 'RAWM-*.txt' | ForEach-Object {$_.FullName}
    }
}
function Invoke-Roman([string]$Answer,[string]$Name) {
    $start=[Diagnostics.ProcessStartInfo]::new((Get-Command pwsh.exe).Source)
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($arg in @('-NoLogo','-NoProfile','-Command','roman')) { $start.ArgumentList.Add($arg) }
    $process=[Diagnostics.Process]::Start($start)
    try {
        $stdout=$process.StandardOutput.ReadToEndAsync(); $stderr=$process.StandardError.ReadToEndAsync()
        foreach ($line in @('Open Notepad and write hello green world',$Answer,'/exit')) { $process.StandardInput.WriteLine($line) }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(50000)) { throw 'roman entry test timed out.' }
        $output=$stdout.GetAwaiter().GetResult(); $errors=$stderr.GetAwaiter().GetResult()
        [IO.File]::WriteAllText((Join-Path $fixture ($Name+'.txt')),$output+$errors)
        if ($process.ExitCode -ne 0 -or $errors -or $output -notmatch 'Approve: y / Decline: n' -or $output -match '/act|/agent|Planning locally|RAWM \| CODE') {
            throw "Natural-language entry failed. See $fixture"
        }
        return $output
    } finally {
        if (-not $process.HasExited) { $process.Kill($true) }
        $process.Dispose()
    }
}
$before=@(Get-DraftPaths)
$declined=Invoke-Roman 'n' 'declined'
$afterDecline=@(Get-DraftPaths)
if ($declined -notmatch 'Canceled. No actions ran.' -or $afterDecline.Count -ne $before.Count -or @($afterDecline | Where-Object {$_ -notin $before}).Count) {
    throw 'Declining the request did not leave drafts unchanged.'
}
Write-Host 'PASS: roman requested y/n; n canceled without creating a Notepad draft.'
if ($Approve) {
    $approved=Invoke-Roman 'y' 'approved'
    Write-Host $approved
    if ($approved -notmatch 'Opened Notepad and verified 17 characters in draft (?<marker>RAWM-[a-f0-9]+)') {
        throw "Live Notepad action was not verified. See $fixture\approved.txt"
    }
    $marker=$Matches.marker
    $newDrafts=@(Get-DraftPaths | Where-Object {$_ -notin $afterDecline})
    if ($newDrafts.Count -ne 1 -or [IO.Path]::GetFileNameWithoutExtension($newDrafts[0]) -cne $marker -or (Get-Item -LiteralPath $newDrafts[0]).Length -ne 0) {
        throw 'Expected exactly one new empty scratch file for the unsaved Notepad draft.'
    }
    # Independent, read-only observation after roman exits. No typing or focus changes.
    $legacy=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $observation=& $legacy -NoProfile -NonInteractive -STA -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Inspect-RAWMNotepad.ps1') -Marker $marker
    [IO.File]::WriteAllText((Join-Path $fixture 'visible-notepad.json'),($observation -join "`n"))
    $view=$observation | ConvertFrom-Json
    if ($view.status -ne 'verified' -or $view.text -cne 'hello green world') { throw 'Independent Notepad read-back failed.' }
    Write-Host 'PASS: y opened Notepad; independent UI Automation read-back found exactly hello green world in its visible editor.'
}
Write-Host "Evidence: $fixture"
