$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fixture=Join-Path $PSScriptRoot ('.runs\code-draft-live-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
Import-Module (Join-Path $root 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root,$fixture)
    $script:Root=$root
    $script:Settings=Read-RAWMJson (Join-Path $root 'config\settings.json')
    Initialize-RAWMAgent
    $script:Agent.Storage=Join-Path $fixture 'agent'
    $script:Agent.Workspace=Join-Path $fixture 'workspace'
    $clock=[Diagnostics.Stopwatch]::StartNew()
    try {
        $result=Submit-RAWMAgentRequest 'open notepad and write an html program that says Hello World, with a button that makes the letters explode and then resets so the cycle can repeat'
        if ($result -notlike 'Approve: y*') { throw 'Expected generated-code approval.' }
        $plan=$script:Agent.Pending.Json | ConvertFrom-Json -AsHashtable
        if ($plan.steps.Count -ne 1 -or $plan.steps[0].tool -ne 'notepad.write') { throw 'Unexpected tool for generated draft.' }
        $html=$plan.steps[0].arguments.text
        if ($html -notmatch '(?i)hello\s*world' -or $html -notmatch '(?i)<script|onclick|animation') { throw 'Generated sample is missing the requested message or interaction.' }
        [IO.File]::WriteAllText((Join-Path $fixture 'generated.html'),$html)
        $null=Invoke-RAWMConversationControl 'n'
        if (Test-Path (Join-Path $script:Agent.Storage 'drafts')) { throw 'Draft opened before approval.' }
        New-RAWMSession
        Add-RAWMMessage user 'Reply with the single word ready.'
        $answer=Invoke-RAWMCompletion fast
        if ($answer.Trim() -notmatch '^(?i)ready[.!]?$') { throw "Unexpected streaming chat result: $answer" }
        [IO.File]::WriteAllText((Join-Path $fixture 'results.json'),(@{seconds=$clock.Elapsed.TotalSeconds;codeCharacters=$html.Length;chat=$answer;approved=$false}|ConvertTo-Json))
        Write-Host "PASS: real local code generation, approval cancellation, and streaming chat. Evidence: $fixture"
    } finally { Clear-RAWMPendingPlan; Stop-RAWMServer }
} $root $fixture
