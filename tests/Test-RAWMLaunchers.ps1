$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fixture=Join-Path $PSScriptRoot ('.runs\launchers-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
$modern=(Get-Command pwsh.exe -ErrorAction Stop).Source
$legacy=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$cmd=Join-Path $env:SystemRoot 'System32\cmd.exe'
$shells=@(
    @{Name='PowerShell7';Exe=$modern;Arguments=@('-NoLogo','-NoProfile','-Command','roman')},
    @{Name='WindowsPowerShell';Exe=$legacy;Arguments=@('-NoLogo','-NoProfile','-Command','roman')},
    @{Name='CommandPrompt';Exe=$cmd;Arguments=@('/d','/c','roman')}
)
foreach ($shell in $shells) {
    $start=[Diagnostics.ProcessStartInfo]::new($shell.Exe)
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($argument in $shell.Arguments) {$start.ArgumentList.Add($argument)}
    $process=[Diagnostics.Process]::Start($start)
    try {
        $out=$process.StandardOutput.ReadToEndAsync(); $err=$process.StandardError.ReadToEndAsync()
        foreach ($line in @('turn agent off','Open Notepad and write hello green world','turn agent on','/workers','open vs code and write a simple c program','n','Open Notepad and write hello green world','n','open note pad and write - hello green world /agent','n','Show system info','y','/exit')) { $process.StandardInput.WriteLine($line) }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(20000)) { throw "$($shell.Name) launcher timed out." }
        $output=$out.GetAwaiter().GetResult()
        $errors=$err.GetAwaiter().GetResult()
        [IO.File]::WriteAllText((Join-Path $fixture ($shell.Name+'.txt')),$output+$errors)
        if ($process.ExitCode -ne 0 -or $errors -or $output -notmatch 'roman' -or $output -notmatch 'LOCAL\s+\|\s+Private' -or $output -match 'Describe what you want to do|Actions ask for y / n' -or $output -notmatch 'Agent OFF. Chat only.' -or $output -notmatch 'Agent is off.' -or $output -notmatch 'Selection: pi' -or $output -notmatch 'Run this task using pi' -or $output -notmatch 'processors:' -or $output -notmatch 'roman closed.' -or ([regex]::Matches($output,'Canceled. No actions ran.')).Count -ne 3 -or $output -match 'Planning locally|roman \| CODE|/act|/agent') {
            throw "Launcher verification failed for $($shell.Name). See $fixture"
        }
        Write-Host "PASS: roman via $($shell.Name) (agent toggle, disabled action, local tool, clean exit)."
    } finally {
        if (-not $process.HasExited) { $process.Kill($true) }
        $process.Dispose()
    }
}
$start=[Diagnostics.ProcessStartInfo]::new($legacy)
$start.UseShellExecute=$false; $start.CreateNoWindow=$true
$start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
foreach ($argument in @('-NoLogo','-NoProfile','-NonInteractive','-STA','-ExecutionPolicy','Bypass','-File',(Join-Path $root 'app\WindowsNotepad.ps1'),'-CheckOnly')) { $start.ArgumentList.Add($argument) }
$process=[Diagnostics.Process]::Start($start)
try {
    $out=$process.StandardOutput.ReadToEndAsync(); $err=$process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(20000)) { throw 'Adapter compilation timed out.' }
    $output=$out.GetAwaiter().GetResult(); $errors=$err.GetAwaiter().GetResult()
    [IO.File]::WriteAllText((Join-Path $fixture 'adapter-compile.txt'),$output+$errors)
    if ($errors -or ($output | ConvertFrom-Json).status -ne 'compiled') { throw "Adapter compilation failed: $output $errors" }
    Write-Host 'PASS: Windows UI Automation adapter compiles (no application opened).'
} finally {
    if (-not $process.HasExited) { $process.Kill() }
    $process.Dispose()
}
Write-Host "Launcher evidence: $fixture"
