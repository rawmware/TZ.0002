function Resolve-RAWMBrowserUrl {
    param([string]$Url)
    if ($Url -ceq 'about:blank') { return $Url }
    if ($Url.Length -gt 2048 -or $Url -match '[\s\x00-\x1f\x7f"<>\\]' -or (Test-RAWMSecretText $Url)) {
        throw 'Use a web address without spaces, credentials, or control characters.'
    }
    $uri=$null
    if (-not [Uri]::TryCreate($Url,[UriKind]::Absolute,[ref]$uri) -or $uri.Scheme -notin @('https','http') -or
        -not $uri.Host -or $uri.UserInfo) { throw 'Browser actions accept only http:// or https:// web addresses without embedded credentials.' }
    return $uri.AbsoluteUri
}

function Get-RAWMBrowserRequest {
    param([string]$Text)
    $s=ConvertTo-RAWMActionText $Text
    $browserPattern='(?:(?:the|a|my)\s+)?(?:web\s+browser|browser|google\s+chrome|chrome|microsoft\s+edge|edge)(?:\s+or\s+(?:(?:the|a)\s+)?(?:google\s+chrome|chrome|microsoft\s+edge|edge)(?:\s+browser)?)?'
    $target=$null; $browser='default'
    if ($s -match "^(?i)(?:open|launch|start)\s+(?<browser>$browserPattern)(?:\s*,?\s+(?:and\s+(?:then\s+)?|then\s+|and\s+once\s+it\s+is\s+opened\s+)(?:(?:can|could)\s+(?:you\s+)?)?(?:go\s+to|navigate\s+to|open(?:\s+up)?|visit)\s+(?<target>.+))?[.!?]?$" ) {
        $target=$Matches['target']; $chosen=$Matches.browser
        if ($chosen -notmatch '\bor\b') {
            if ($chosen -match 'chrome') { $browser='chrome' }
            elseif ($chosen -match 'edge') { $browser='edge' }
        }
        if (-not $target) { return @{browser=$browser;url='about:blank'} }
    } elseif ($s -match '^(?i)(?:open(?:\s+up)?|visit|go\s+to|navigate\s+to)\s+(?<target>.+)$') { $target=$Matches.target }
    else { return $null }
    $target=$target -replace '(?i)\s+for\s+me[.!?]?$', ''
    $target=$target.Trim().TrimEnd([char[]]'!')
    # A YouTube search opens the visible results page; it does not claim to watch videos.
    if ($target -match '^(?i)youtube(?:\.com)?(?:/)?(?:\s+for\s+me)?\s*,?\s*(?:and\s+)?(?:search(?:\s+for)?|find|pull\s+up|show(?:\s+me)?)\s+(?:some\s+)?(?<query>.+?)[?!.]?$') {
        $query=$Matches.query.Trim()
        if ($query -match '(?i)\b(?:and|then)\s+(?:open|delete|send|run|install|download)\b') { return $null }
        return @{browser=$browser;url=('https://www.youtube.com/results?search_query='+[Uri]::EscapeDataString($query))}
    }
    $target=$target.TrimEnd([char[]]'.')
    if ($target -match '^(?i)youtube(?:\.com)?/?$') { $target='https://www.youtube.com/' }
    elseif ($target -match '^(?i)(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#][^\s]*)?$') { $target='https://'+$target }
    elseif ($target -notmatch '^https?://\S+$') { return $null }
    try { $url=Resolve-RAWMBrowserUrl $target } catch { return $null }
    return @{browser=$browser;url=$url}
}

function Get-RAWMBrowserExecutable {
    param([string]$Browser)
    $choices=if ($Browser -eq 'default') { @('edge','chrome') } else { @($Browser) }
    foreach ($choice in $choices) {
        $relative=if ($choice -eq 'chrome') {'Google\Chrome\Application\chrome.exe'} else {'Microsoft\Edge\Application\msedge.exe'}
        foreach ($base in @($env:ProgramFiles,${env:ProgramFiles(x86)},$env:LOCALAPPDATA)) {
            if (-not $base) { continue }
            $path=Join-Path $base $relative
            if (Test-Path -LiteralPath $path -PathType Leaf) { return @{Name=$choice;Path=$path} }
        }
    }
    throw 'No supported browser was found. Install Chrome or Edge, or name the one already installed.'
}

function Invoke-RAWMBrowser {
    param([string]$Browser,[string]$Url)
    $url=Resolve-RAWMBrowserUrl $Url
    $app=Get-RAWMBrowserExecutable $Browser
    $start=[Diagnostics.ProcessStartInfo]::new($app.Path)
    $start.UseShellExecute=$false
    $start.ArgumentList.Add('--new-window'); $start.ArgumentList.Add($url)
    $process=[Diagnostics.Process]::Start($start)
    if (-not $process) { throw 'Windows did not accept the browser launch.' }
    $process.Dispose()
    return "Sent $url to $($app.Name) in a new window. Page loading has not been verified."
}
