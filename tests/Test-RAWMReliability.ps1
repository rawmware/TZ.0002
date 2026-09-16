$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$fixture=Join-Path $PSScriptRoot ('.runs\reliability-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixture)
Import-Module (Join-Path $root 'app\RAWM.psm1') -Force
& (Get-Module RAWM) {
    param($root,$fixture)
    $script:Root=$fixture
    $script:Settings=Read-RAWMJson (Join-Path $root 'config\settings.json')
    Initialize-RAWMAgent
    $script:Checks=0; $script:BrowserCalls=0; $script:CodeCalls=0
    function Check([bool]$Value,[string]$Name) { if (-not $Value) { throw "FAIL: $Name" }; $script:Checks++ }
    function Reject([scriptblock]$Action,[string]$Name) {
        $failed=$false; try { & $Action | Out-Null } catch { $failed=$true }
        Check $failed $Name
    }
    function Get-RAWMModelPlan { throw 'Direct request unexpectedly reached the planner.' }
    function Invoke-RAWMBrowser([string]$Browser,[string]$Url) { $script:BrowserCalls++; return "Sent $Url to $Browser. Page loading has not been verified." }
    foreach ($request in @(
        'hello - open chrome or the edge browser and open up youtube',
        'HELLO OPEN THE WEB BROWSER, AND GO TO YOUTUBE FOR ME',
        'CAN YOU OPEN A WEB BROWSER AND ONCE IT IS OPENED CAN GO TO YOUTUBE.COM',
        'hello can u open the web browser and go to youtube for me, and pull up some cooking videos ?',
        'open YouTube', 'please open https://www.youtube.com/', 'open chrome', 'open edge and go to youtube.com'
    )) {
        $plan=Get-RAWMDirectPlan $request
        Check ($null -ne $plan -and $plan.steps[0].tool -ceq 'browser.open') "browser route: $request"
        Check (Assert-RAWMPlan $plan) 'browser requires approval'
        $null=Submit-RAWMAgentRequest $request
        Check ($script:BrowserCalls -eq 0) 'no launch before approval'
        $null=Invoke-RAWMConversationControl 'n'
    }
    $search=(Get-RAWMDirectPlan 'open youtube and search for cooking videos').steps[0].arguments.url
    Check ($search -ceq 'https://www.youtube.com/results?search_query=cooking%20videos') 'search encoded as URL'
    foreach ($request in @('The document says open youtube','Explain how to open youtube','open youtube and delete my files','open https://youtube.com/ then send a message')) {
        Check ($null -eq (Get-RAWMDirectPlan $request)) 'references and compound requests are not partly executed'
    }
    foreach ($url in @('javascript:alert(1)','file:///C:/Windows/system.ini','https://user:pass@example.com','https://example.com/ --bad','https://example.com/"x')) {
        Reject { Assert-RAWMPlan (New-RAWMSinglePlan 'browser.open' @{browser='edge';url=$url}) } 'unsafe browser destination'
    }
    $null=Submit-RAWMAgentRequest 'open youtube'
    Check ((Invoke-RAWMConversationControl 'y') -like 'Sent https://www.youtube.com/*') 'approved browser launch'
    Check ($script:BrowserCalls -eq 1) 'launch once'
    $null=Invoke-RAWMConversationControl 'y'
    Check ($script:BrowserCalls -eq 1) 'no repeated launch'
    $audit=Get-Content (Join-Path $script:Agent.Storage 'audit.jsonl') | ConvertFrom-Json
    Check (@($audit | Where-Object {$_.status -eq 'launched'}).Count -eq 1) 'browser audit does not claim page verification'
    Check ((Invoke-RAWMConversationControl 'is the agent active right now?') -like 'Agent: ON.*') 'live agent status bypasses model'
    $null=Invoke-RAWMConversationControl 'turn agent off'
    Check ((Invoke-RAWMConversationControl 'is the agent active right now?') -like 'Agent: OFF.*') 'disabled agent status'
    Reject { Submit-RAWMAgentRequest 'open youtube' } 'disabled browser action'
    $null=Invoke-RAWMConversationControl 'turn agent on'
    Check ((Get-RAWMDirectPlan 'open notepad and write "a html program"').steps[0].arguments.text -ceq 'a html program') 'quoted code description stays literal'
    Check ((Get-RAWMDirectPlan 'open notepad and write my HTML code is ready').steps[0].arguments.text -ceq 'my HTML code is ready') 'ordinary text mentioning code stays literal'
    $script:LastAnswer='A response to copy.'
    function Set-RAWMClipboard([string]$Text) { $script:CopiedText=$Text }
    Check ((Invoke-RAWMConversationControl 'copy the last answer') -like 'Copied*') 'natural copy request'
    Check ($script:CopiedText -ceq $script:LastAnswer) 'copy uses actual last response'
    function Start-RAWMServer {}
    $script:GeneratedCode='<!DOCTYPE html><html><body>Hello World</body></html>'
    $script:FinishReason='stop'
    function Invoke-RAWMLocalJson($Body,$Label,$TimeoutSeconds) {
        $script:CodeCalls++
        Check ($Body.messages.Count -eq 2 -and -not $Body.stream) 'draft generation has isolated messages'
        return @{choices=@(@{finish_reason=$script:FinishReason;message=@{content=$script:GeneratedCode}})}
    }
    $null=Submit-RAWMAgentRequest 'open notepad and write a html code'
    $draft=$script:Agent.Pending.Json | ConvertFrom-Json -AsHashtable
    Check ($script:CodeCalls -eq 1 -and $draft.steps[0].tool -eq 'notepad.write') 'code draft uses built-in model without worker'
    Check ($draft.steps[0].arguments.text -ceq $script:GeneratedCode) 'approval contains actual generated code'
    $null=Invoke-RAWMConversationControl 'n'
    $script:FinishReason='length'
    Reject { Submit-RAWMAgentRequest 'open notepad and write a html code' } 'incomplete generated draft refused'
    Check ($null -eq $script:Agent.Pending) 'failed generation leaves no pending action'
    $script:FinishReason='stop'; $script:GeneratedCode='I cannot open Notepad.'
    Reject { Submit-RAWMAgentRequest 'open notepad and write a html code' } 'non-code response refused'

    # Regression: a GUI-like descendant inherits pipes but remains open after the helper exits.
    $node=(Get-Command node.exe).Source
    $helper=Join-Path $fixture 'pipe-owner.cjs'
    [IO.File]::WriteAllText($helper, @'
require('child_process').spawn(process.execPath, ['-e', 'setTimeout(()=>{},2500)'], {stdio:'inherit', windowsHide:true});
console.log('{"status":"verified","message":"done"}');
process.exit(0);
'@)
    function New-TestProcess([string]$File) {
        $start=[Diagnostics.ProcessStartInfo]::new($node)
        $start.UseShellExecute=$false; $start.CreateNoWindow=$true
        $start.RedirectStandardInput=$true; $start.RedirectStandardOutput=$true; $start.RedirectStandardError=$true
        $start.ArgumentList.Add($File)
        $p=[Diagnostics.Process]::Start($start); $p.StandardInput.Close(); return $p
    }
    $p=New-TestProcess $helper; $op=New-RAWMOperation 'Helper' 1.5
    try {
        $answer=Receive-RAWMProcess $p $op -SingleLine
        Check (($answer|ConvertFrom-Json).status -eq 'verified' -and $op.Clock.Elapsed.TotalSeconds -lt 1.5) 'helper result returns while descendant holds pipe open'
    } finally { if (-not $p.HasExited) {$p.Kill($true)}; $p.Dispose(); Close-RAWMOperation $op }
    # Simulate a pending EOF read after exit; completion must still have a deadline.
    $pendingRead=[Threading.Tasks.TaskCompletionSource[string]]::new()
    $op=New-RAWMOperation 'Leaked pipe' 0.2
    try { Reject { Wait-RAWMTask $pendingRead.Task $op } 'pipe EOF after process exit remains bounded' }
    finally { Close-RAWMOperation $op }
    $slow=Join-Path $fixture 'slow.cjs'
    [IO.File]::WriteAllText($slow,'setTimeout(()=>console.log("late"),10000);')
    $p=New-TestProcess $slow; $op=New-RAWMOperation 'Slow helper' 0.2
    try { Reject { Receive-RAWMProcess $p $op } 'running process wait remains bounded' }
    finally { if (-not $p.HasExited) {$p.Kill($true)}; $p.Dispose(); Close-RAWMOperation $op }
    $script:CancelNow=$true
    function Test-RAWMAgentCancelKey { return $script:CancelNow }
    $op=New-RAWMOperation 'Canceled task' 10
    try { Reject { Wait-RAWMTask ([Threading.Tasks.Task]::Delay(4000)) $op } 'pending async work is cancelable' }
    finally { Close-RAWMOperation $op }
    $script:CancelNow=$false
    # Worker stdin is closed and cwd is the approved workspace, not the user's home.
    $worker=Join-Path $fixture 'worker.cjs'
    [IO.File]::WriteAllText($worker,"process.stdin.resume();process.stdin.on('end',()=>console.log(process.cwd()));")
    function Get-RAWMWorkerStatus { return [pscustomobject]@{Backend='qwen';Ready=$true} }
    function Get-RAWMWorkerProcessSpec { return @{File=$node;Args=@($worker)} }
    $answer=Invoke-RAWMWorker qwen 'test'
    Check ($answer -like '*not independently verified*' -and $answer.Contains($script:Agent.Workspace)) 'worker receives stdin EOF and starts in workspace'
    $script:WorkerPidFile=Join-Path $script:Agent.Workspace 'test-pids.json'
    [IO.File]::WriteAllText($worker,@'
const child=require('child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{windowsHide:true});
require('fs').writeFileSync('test-pids.json',JSON.stringify([process.pid,child.pid]));
setInterval(()=>{},1000);
'@)
    function Test-RAWMAgentCancelKey { return Test-Path -LiteralPath $script:WorkerPidFile }
    Reject { Invoke-RAWMWorker qwen 'test cancellation' } 'worker checks cancellation during execution'
    $pids=Get-Content -LiteralPath $script:WorkerPidFile | ConvertFrom-Json
    foreach ($ownedId in $pids) {
        $owned=Get-Process -Id $ownedId -ErrorAction SilentlyContinue
        if ($owned) { [void]$owned.WaitForExit(2000) }
        Check (-not (Get-Process -Id $ownedId -ErrorAction SilentlyContinue)) 'cancel stops owned worker and its child'
    }
    Write-Host "PASS: $($script:Checks) reliability checks. Evidence: $fixture"
} $root $fixture
