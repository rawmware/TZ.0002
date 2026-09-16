# Read-only desktop observation of the unique test draft, run in Windows PowerShell STA.
param([Parameter(Mandatory)][ValidatePattern('^RAWM-[a-f0-9]{32}$')][string]$Marker)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
try {
    $windows=[Windows.Automation.AutomationElement]::RootElement.FindAll(
        [Windows.Automation.TreeScope]::Children,
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Window))
    $found=@($windows | Where-Object {$_.Current.Name.Contains($Marker) -and (Get-Process -Id $_.Current.ProcessId).ProcessName -eq 'Notepad'})
    if ($found.Count -ne 1 -or $found[0].Current.IsOffscreen) { throw 'A unique visible test window was not found.' }
    $editors=$found[0].FindAll([Windows.Automation.TreeScope]::Descendants,
        [Windows.Automation.OrCondition]::new(
            [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Document),
            [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Edit)))
    $matches=@()
    foreach ($editor in $editors) {
        if ($editor.Current.IsOffscreen -or -not $editor.Current.IsEnabled) { continue }
        $pattern=$null
        if ($editor.TryGetCurrentPattern([Windows.Automation.TextPattern]::Pattern,[ref]$pattern)) {
            $text=$pattern.DocumentRange.GetText(4002).Replace("`r`n","`n").Replace("`r","`n")
            if ($text -ceq 'hello green world') { $matches+=@{text=$text;editorClass=$editor.Current.ClassName} }
        }
    }
    if ($matches.Count -ne 1) { throw 'Exactly one visible editor containing the expected text was not found.' }
    @{status='verified';text=$matches[0].text;editorClass=$matches[0].editorClass;window=$found[0].Current.Name;processId=$found[0].Current.ProcessId} | ConvertTo-Json -Compress
} catch {
    @{status='failed';message=$_.Exception.Message} | ConvertTo-Json -Compress
    exit 1
}
