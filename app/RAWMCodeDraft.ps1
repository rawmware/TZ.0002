function Get-RAWMCodeDraftRequest {
    param([string]$Text)
    $s=ConvertTo-RAWMActionText $Text
    if ($s -notmatch '^(?i)(?:open|launch|start)\s+(?:the\s+)?note\s*pad\s*(?:,\s*)?(?:and(?:\s+then)?|then|to)\s+(?:write|create|make|generate)\s+(?<request>.+)$') { return $null }
    $request=$Matches.request
    if ($request -notmatch '^(?i)(?:(?:a|an|the|some|new|simple|small|short|basic|complete)\s+)*(?:html|css|javascript|typescript|python|powershell|java|rust|c\+\+|code|program|script|website|webpage)\b') { return $null }
    # This path prepares text only. Requests to save/run or act elsewhere need a different plan.
    if ($request -match '(?i)\b(?:and|then)\s+(?:open|save|run|execute|delete|send|install|download|close|rename)\b') { return $null }
    return $request
}

function New-RAWMCodeDraftPlan {
    param([string]$Request)
    if ($Request.Length -gt 4000) { throw 'Code requests must be under 4000 characters.' }
    if ('notepad.write' -cnotin $script:Agent.Tools) { throw 'Notepad actions are not enabled in this installation.' }
    Write-RAWMColor 'Preparing code with the local coding model. No application has opened yet. Esc or Ctrl+C cancels.' Gray
    Start-RAWMServer code
    $model=Get-RAWMModelConfig code
    $body=@{
        model=$model.Name; stream=$false; temperature=0.15; max_tokens=1800
        chat_template_kwargs=@{enable_thinking=$false}
        messages=@(
            @{role='system';content='Write the complete compact source code requested by the user. Return only code, without markdown fences or explanations. Aim for under 4000 characters; avoid verbose styling. For HTML use one self-contained HTML document with inline CSS/JS and no external dependencies. Code will be placed in an unsaved Notepad draft for review, not executed. Do not claim to open or save anything. Do not include placeholders or omitted sections.'},
            @{role='user';content=$Request}
        )
    }
    $result=Invoke-RAWMLocalJson $body 'Generating code locally' 120
    if ($result.choices[0].finish_reason -ne 'stop') { throw 'The generated draft was incomplete. Nothing opened; ask for a smaller program.' }
    $code=([string]$result.choices[0].message.content).Trim()
    if ($code -match '(?s)^```[^\r\n]*\r?\n(?<code>.*?)\r?\n```$') { $code=$Matches.code }
    if (-not $code -or $code.Length -gt 16000) { throw 'The generated draft was empty or exceeded 16000 characters. Nothing opened; ask for a smaller program.' }
    if ($Request -match '(?i)\bhtml\b' -and ($code -notmatch '(?i)<html\b' -or $code -notmatch '(?i)</html>\s*$')) {
        throw 'The local model did not return a complete HTML document. Nothing opened.'
    }
    $plan=New-RAWMSinglePlan 'notepad.write' @{text=$code}
    [void](Assert-RAWMPlan $plan)
    return $plan
}
