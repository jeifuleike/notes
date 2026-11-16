param(
    [string]$VaultPath = "",
    [ValidateSet("all-projects", "vault-only")]
    [string]$Scope = "all-projects",
    [int]$MinChars = 80,
    [switch]$EnableCaptureHook,
    [switch]$Disable,
    [switch]$SkipAgents
)

$ErrorActionPreference = "Stop"
$SourceDir = $PSScriptRoot
$VaultRoot = if ($VaultPath) { (Resolve-Path -LiteralPath $VaultPath).Path } else { (Resolve-Path -LiteralPath (Join-Path $SourceDir "..\..")).Path }
$CodexHome = Join-Path $env:USERPROFILE ".codex"
$HooksDir = Join-Path $CodexHome "hooks"
$SkillsDir = Join-Path $CodexHome "skills"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$HookEnabled = $EnableCaptureHook -and -not $Disable

New-Item -ItemType Directory -Force -Path $CodexHome, $HooksDir, $SkillsDir | Out-Null

$HookScriptSource = Join-Path $SourceDir "kb-capture-ask.py"
$HookScriptTarget = Join-Path $HooksDir "kb-capture-ask.py"
if ($HookEnabled) {
    if (Test-Path -LiteralPath $HookScriptTarget) {
        Copy-Item -LiteralPath $HookScriptTarget -Destination "$HookScriptTarget.bak-$Stamp" -Force
    }
    Copy-Item -LiteralPath $HookScriptSource -Destination $HookScriptTarget -Force
}

$HooksFile = Join-Path $CodexHome "hooks.json"
$HookCommand = "python `"$HookScriptTarget`""
$hooksConfig = @{}
if (Test-Path -LiteralPath $HooksFile) {
    $hooksConfig = Get-Content -LiteralPath $HooksFile -Raw | ConvertFrom-Json -AsHashtable
}
if (-not $hooksConfig.ContainsKey("hooks") -or $null -eq $hooksConfig["hooks"]) {
    $hooksConfig["hooks"] = @{}
}
if (-not $hooksConfig["hooks"].ContainsKey("Stop") -or $null -eq $hooksConfig["hooks"]["Stop"]) {
    $hooksConfig["hooks"]["Stop"] = @()
}
$stopHooks = @($hooksConfig["hooks"]["Stop"])
$hookChanged = $false
if ($HookEnabled) {
    $exists = $false
    foreach ($entry in $stopHooks) {
        foreach ($hook in @($entry["hooks"])) {
            if ($hook["command"] -like "*kb-capture-ask.py*") {
                if ($hook["command"] -ne $HookCommand) {
                    $hook["command"] = $HookCommand
                    $hookChanged = $true
                }
                $exists = $true
            }
        }
    }
    if (-not $exists) {
        $stopHooks += @{
            hooks = @(
                @{
                    type = "command"
                    command = $HookCommand
                    timeout = 20
                }
            )
        }
        $hookChanged = $true
    }
} else {
    $filteredHooks = @()
    foreach ($entry in $stopHooks) {
        $remaining = @()
        foreach ($hook in @($entry["hooks"])) {
            if ($hook["command"] -like "*kb-capture-ask.py*") {
                $hookChanged = $true
            } else {
                $remaining += $hook
            }
        }
        if (@($remaining).Count -gt 0) {
            $entry["hooks"] = $remaining
            $filteredHooks += $entry
        }
    }
    $stopHooks = $filteredHooks
}
if ($hookChanged) {
    $hooksConfig["hooks"]["Stop"] = $stopHooks
    $hooksJson = $hooksConfig | ConvertTo-Json -Depth 20
    if (Test-Path -LiteralPath $HooksFile) {
        Copy-Item -LiteralPath $HooksFile -Destination "$HooksFile.bak-$Stamp" -Force
    }
    [System.IO.File]::WriteAllText($HooksFile, $hooksJson, (New-Object System.Text.UTF8Encoding $false))
}

$CaptureConfigFile = Join-Path $CodexHome "kb-capture.json"
$captureConfig = @{
    enabled = $HookEnabled
    vault = $VaultRoot
    scope = $Scope
    cooldown_minutes = 20
    min_chars = $MinChars
}
if (Test-Path -LiteralPath $CaptureConfigFile) {
    try {
        $existing = Get-Content -LiteralPath $CaptureConfigFile -Raw | ConvertFrom-Json -AsHashtable
        foreach ($key in $existing.Keys) {
            if ($key -notin @("vault", "scope", "enabled", "min_chars")) {
                $captureConfig[$key] = $existing[$key]
            }
        }
        Copy-Item -LiteralPath $CaptureConfigFile -Destination "$CaptureConfigFile.bak-$Stamp" -Force
    } catch {
        Copy-Item -LiteralPath $CaptureConfigFile -Destination "$CaptureConfigFile.bak-$Stamp" -Force
    }
}
[System.IO.File]::WriteAllText($CaptureConfigFile, ($captureConfig | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding $false))

$AssetsConfigFile = Join-Path $CodexHome "codex-assets.json"
$assetsConfig = @{
    vault = $VaultRoot
    skills_dir = "80-Skill库/Codex备份/skills"
    prompt_backup = "90-知识系统/prompts/AGENTS.global.md"
    sync_skills = @("kb-curator", "kb-query", "codex-asset-sync")
}
if (Test-Path -LiteralPath $AssetsConfigFile) {
    Copy-Item -LiteralPath $AssetsConfigFile -Destination "$AssetsConfigFile.bak-$Stamp" -Force
}
[System.IO.File]::WriteAllText($AssetsConfigFile, ($assetsConfig | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding $false))

function Copy-KbSkill {
    param([string]$Name)
    $target = Join-Path $VaultRoot "80-Skill库\Codex备份\skills\$Name"
    $destination = Join-Path $SkillsDir $Name
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Warning "Skill 源不存在：$target"
        return
    }
    if (Test-Path -LiteralPath $destination) {
        $item = Get-Item -LiteralPath $destination -Force
        if ($item.LinkType -in @("Junction", "SymbolicLink")) {
            Remove-Item -LiteralPath $destination -Force
        } else {
            $backup = Join-Path $CodexHome "skill-backups\$Stamp\skills\$Name"
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
            Copy-Item -LiteralPath $destination -Destination $backup -Recurse -Force
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
    }
    Copy-Item -LiteralPath $target -Destination $destination -Recurse -Force
    Write-Host "已复制：$destination"
}

Copy-KbSkill -Name "kb-curator"
Copy-KbSkill -Name "kb-query"
Copy-KbSkill -Name "codex-asset-sync"

if (-not $SkipAgents) {
    $AgentsFile = Join-Path $CodexHome "AGENTS.md"
    $BeginMarker = "<!-- BEGIN codex-kb -->"
    $EndMarker = "<!-- END codex-kb -->"
    $Block = Get-Content -LiteralPath (Join-Path $VaultRoot "90-知识系统\prompts\AGENTS.global.md") -Raw
    if (-not $Block.TrimStart().StartsWith($BeginMarker)) {
        $Block = $BeginMarker + "`n" + $Block.Trim() + "`n" + $EndMarker
    }
    $existingText = ""
    if (Test-Path -LiteralPath $AgentsFile) {
        $existingText = Get-Content -LiteralPath $AgentsFile -Raw
        if ($null -eq $existingText) {
            $existingText = ""
        }
    }
    if (Test-Path -LiteralPath $AgentsFile) {
        Copy-Item -LiteralPath $AgentsFile -Destination "$AgentsFile.bak-$Stamp" -Force
    }
    $pattern = "(?s)$([regex]::Escape($BeginMarker)).*?$([regex]::Escape($EndMarker))"
    if ($existingText -match $pattern) {
        $updated = [regex]::Replace($existingText, $pattern, "")
    } else {
        $updated = $existingText
    }
    $updated = $updated.TrimEnd() + "`n`n" + $Block.TrimEnd() + "`n"
    [System.IO.File]::WriteAllText($AgentsFile, $updated, (New-Object System.Text.UTF8Encoding $false))
}

Write-Host ""
Write-Host "安装完成。"
Write-Host "Vault: $VaultRoot"
Write-Host "Scope: $Scope"
Write-Host "Hook:  $(if ($HookEnabled) { $HookScriptTarget } else { 'disabled' })"
Write-Host "Config: $CaptureConfigFile"
Write-Host "Assets: $AssetsConfigFile"
Write-Host ""
Write-Host "下一步："
Write-Host "1. Skill 已复制到 ~/.codex/skills，不依赖 notes 的 junction。"
Write-Host "2. 需要主动询问 Hook 时再加 -EnableCaptureHook，并执行 /hooks 审核。"
Write-Host "3. 公司机器把 -Scope 改成 vault-only；同步资产用 codex-asset-sync Skill。"
