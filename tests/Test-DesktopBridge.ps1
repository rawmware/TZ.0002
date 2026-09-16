$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$env:Path=(Join-Path $env:LOCALAPPDATA 'TZ/bin')+';'+$env:Path
$env:TZ_HOME=$root
$id='bridge-'+[guid]::NewGuid().ToString('N')
$fixture=Join-Path $PSScriptRoot ('.runs/'+$id)
New-Item -ItemType Directory $fixture -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'context') -Destination $fixture -Recurse
foreach ($shell in @(
    @{Exe='cmd.exe';Args=@('/d','/c','roman -NoBanner')},
    @{Exe='powershell.exe';Args=@('-NoProfile','-Command','roman -NoBanner')},
    @{Exe=(Get-Process -Id $PID).Path;Args=@('-NoProfile','-Command','rom -NoBanner')}
)) {
    $start=[Diagnostics.ProcessStartInfo]::new($shell.Exe)
    $start.UseShellExecute=$false; $start.CreateNoWindow=$true
    $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
    foreach ($argument in $shell.Args) { $start.ArgumentList.Add($argument) }
    $process=[Diagnostics.Process]::Start($start)
    try {
        $out=$process.StandardOutput.ReadToEndAsync(); $err=$process.StandardError.ReadToEndAsync()
        foreach ($line in @('is the agent active right now?','Open Notepad and write bridge check','n','/workers','/model','/exit')) { $process.StandardInput.WriteLine($line) }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(20000)) { throw 'Launcher timed out' }
        $output=$out.GetAwaiter().GetResult(); $errors=$err.GetAwaiter().GetResult()
        [IO.File]::WriteAllText((Join-Path $fixture ([IO.Path]::GetFileName($shell.Exe)+'.txt')),$output+$errors)
        if ($process.ExitCode -ne 0 -or $errors -or $output -notmatch 'Canceled. No actions ran.' -or $output -notmatch 'roman closed.' -or $output -notmatch 'Runtime: ollama') { throw "Launcher failed: $($shell.Exe): $errors" }
        Write-Host "PASS launcher: $($shell.Exe)"
    } finally { if (-not $process.HasExited) {$process.Kill($true)}; $process.Dispose() }
}
Import-Module (Join-Path $root 'app/RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root,$fixture)
    $script:Root=$fixture
    $script:Settings=Read-RAWMJson (Join-Path $root 'config/settings.local.json')
    Initialize-RAWMAgent
    $script:Session=[pscustomobject]@{messages=[Collections.ArrayList]@(@{role='system';content='Answer briefly.'},@{role='user';content='Say ready.'});totals=[pscustomobject]@{promptTokens=0;completionTokens=0;turns=0}}
    Start-RAWMServer code
    if ((Get-RAWMModelConfig code).Name -ne $script:Settings.models.code.name) {throw 'Code model selection failed'}
    $answer=Invoke-RAWMCompletion fast
    if (-not $answer.Trim()) {throw 'Empty live model response'}
    $script:Settings.models.fast.name='missing-model-for-bridge-check'
    $rejected=$false
    try {Start-RAWMServer fast} catch {$rejected=$_.Exception.Message -like '*not installed*'}
    if (-not $rejected) {throw 'Missing model was not rejected'}
    Stop-RAWMServer
    if (-not (Test-RAWMServer)) {throw 'Shared Ollama was stopped'}
    Write-Host 'PASS live Ollama streaming, code selection, missing-model error, shared-service preservation'
} $root $fixture
