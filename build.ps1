# build.ps1 — сборка модов FS19 в ZIP на Windows (аналог build.sh)
#
# Запуск из PowerShell, находясь в папке репозитория:
#
#   .\build.ps1                    # собрать все моды в build\
#   .\build.ps1 FS19_AlphaMoped    # собрать один
#   .\build.ps1 -Install           # собрать и скопировать в папку модов игры
#
# Если PowerShell ругается на запуск скриптов, выполните один раз:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

param(
    [string[]]$Mods,
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Out  = Join-Path $Root "build"

$AllMods = @("FS19_FarmHelper", "FS19_AlphaMoped")
if (-not $Mods -or $Mods.Count -eq 0) { $Mods = $AllMods }

New-Item -ItemType Directory -Force -Path $Out | Out-Null

foreach ($name in $Mods) {
    $src = Join-Path $Root $name

    Write-Host "=============================================="
    Write-Host "  $name"
    Write-Host "=============================================="

    if (-not (Test-Path $src)) {
        Write-Host "  !! нет папки мода: $name" -ForegroundColor Red
        continue
    }

    # проверка XML
    foreach ($f in Get-ChildItem -Path $src -Filter *.xml -Recurse) {
        try {
            [xml](Get-Content $f.FullName -Raw) | Out-Null
            Write-Host "  xml ok  $($f.Name)"
        } catch {
            Write-Host "  !! ошибка XML в $($f.Name): $_" -ForegroundColor Red
        }
    }

    # проверка наличия моделей
    foreach ($f in Get-ChildItem -Path $src -Filter *.xml) {
        $text = Get-Content $f.FullName -Raw
        foreach ($m in [regex]::Matches($text, '<filename>([^<$]+\.i3d)</filename>')) {
            $i3d = $m.Groups[1].Value
            if (-not (Test-Path (Join-Path $src $i3d))) {
                Write-Host "  !! ВНИМАНИЕ: $i3d отсутствует — мод не загрузится." -ForegroundColor Yellow
            } else {
                $shapes = Join-Path $src "$i3d.shapes"
                if (-not (Test-Path $shapes)) {
                    Write-Host "  !! ВНИМАНИЕ: нет $i3d.shapes рядом с моделью." -ForegroundColor Yellow
                }
            }
        }
    }

    $zip = Join-Path $Out "$name.zip"
    if (Test-Path $zip) { Remove-Item $zip }

    Compress-Archive -Path (Join-Path $src "*") -DestinationPath $zip
    $size = [math]::Round((Get-Item $zip).Length / 1MB, 2)
    Write-Host "  -> build\$name.zip  ($size MB)" -ForegroundColor Green
}

if ($Install) {
    $candidates = @(
        "$env:USERPROFILE\Documents\My Games\FarmingSimulator2019\mods",
        "$env:USERPROFILE\OneDrive\Documents\My Games\FarmingSimulator2019\mods",
        "$env:USERPROFILE\Documents\My Games\FarmingSimulator2019\mods"
    )
    $target = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($target) {
        foreach ($name in $Mods) {
            Copy-Item (Join-Path $Out "$name.zip") $target -Force
        }
        Write-Host "==> Установлено в: $target" -ForegroundColor Green
    } else {
        Write-Host "Папка модов FS19 не найдена, скопируйте zip вручную." -ForegroundColor Yellow
    }
}
