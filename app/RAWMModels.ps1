function Get-TZModelChoices {
    $tags=Invoke-RestMethod -Uri ((Get-RAWMBackendUrl)+'/api/tags') -TimeoutSec 5 -NoProxy
    foreach ($m in $tags.models) {
        [pscustomobject]@{Name=$m.name;Installed=$true;Label=('{0}  [installed, {1:N1} GB]' -f $m.name,($m.size/1GB))}
    }
    foreach ($name in @('llama3.2:3b','qwen3:4b','gemma3:4b')) {
        if ($name -notin @($tags.models.name)) {
            [pscustomobject]@{Name=$name;Installed=$false;Label="$name  [download; local model]"}
        }
    }
}

function Select-TZMenu {
    param([array]$Items)
    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected) {
        foreach ($item in $Items) { Write-RAWMColor $item.Label Cyan }
        Write-RAWMColor 'Use /model NAME to select an installed model. Interactive terminals support Up/Down and Enter.' Gray
        return -1
    }
    $index=0
    $previous=[Console]::TreatControlCAsInput
    try {
        [Console]::TreatControlCAsInput=$true
        while ($true) {
            [Console]::Clear()
            Write-RAWMBox 'TZ / MODEL LIBRARY' @('Up / Down: select   Enter: use/download   Esc: back','Installed models plus a curated local download catalog.','Downloads use internet and disk space; inference runs locally.','Larger models may run slowly. Model licenses apply.') Cyan
            $start=[Math]::Max(0,$index-5)
            for ($i=$start;$i -lt [Math]::Min($Items.Count,$start+12);$i++) {
                $mark=if ($i -eq $index) {'> '} else {'  '}
                Write-RAWMColor ($mark+$Items[$i].Label) $(if ($i -eq $index) {'Green'} else {'Gray'})
            }
            $key=[Console]::ReadKey($true)
            if ($key.Key -eq 'Escape' -or ($key.Key -eq 'C' -and $key.Modifiers -band [ConsoleModifiers]::Control)) { return -1 }
            if ($key.Key -eq 'UpArrow') { $index=($index-1+$Items.Count)%$Items.Count }
            if ($key.Key -eq 'DownArrow') { $index=($index+1)%$Items.Count }
            if ($key.Key -eq 'Enter') { return $index }
        }
    } finally { [Console]::TreatControlCAsInput=$previous }
}

function Show-TZModels {
    param([string]$Name)
    if ($script:Settings.backend.type -ne 'ollama') { throw 'The model library requires the Ollama backend.' }
    $items=@(Get-TZModelChoices)
    if ($Name) {
        $chosen=@($items|Where-Object Name -eq $Name)
        if (-not $chosen.Count) { throw 'Model not found. Use /model to see installed models and downloads.' }
        $item=$chosen[0]
    } else {
        $index=Select-TZMenu $items
        if ($index -lt 0) { return }
        $item=$items[$index]
    }
    if (-not $item.Installed) {
        Write-RAWMColor "Download $($item.Name) from Ollama? This may take several GB. Type y to download; anything else cancels." Amber
        if ([Console]::ReadLine() -ine 'y') { return }
        & ollama pull $item.Name
        if ($LASTEXITCODE -ne 0) { throw 'Download did not finish. Current model unchanged.' }
        if ($item.Name -notin @((Get-TZModelChoices|Where-Object Installed).Name)) { throw 'Downloaded model was not found.' }
    }
    $script:Settings.models.fast.name=$item.Name
    # Keep the measured CPU workaround only for the affected tiny model.
    if ($item.Name -eq 'gemma3:1b') { $script:Settings.models.fast|Add-Member numGpu 0 -Force }
    else { $script:Settings.models.fast.PSObject.Properties.Remove('numGpu') }
    $script:Mode='fast'
    Write-RAWMColor "Selected $($item.Name) for chat in this session. /auto restores automatic routing; agent CODE tasks retain their configured model." Green
}
