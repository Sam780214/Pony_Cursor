# ASCII-only; folder name via Unicode scalars (avoids .ps1 file encoding / parser issues)
$ErrorActionPreference = "Stop"
$dist = Join-Path $PSScriptRoot "..\local-only\desktop-pet\dist\DesktopPet"
$exeSrc = Join-Path $dist "DesktopPet.exe"
if (-not (Test-Path -LiteralPath $exeSrc)) {
    Write-Host "ERROR: Missing build output:"
    Write-Host $exeSrc
    Write-Host "Run 快速更新.bat (full pipeline) first."
    exit 1
}
$desk = [Environment]::GetFolderPath("Desktop")
$folder = "$([char]0x684C)$([char]0x9762)$([char]0x5BA0)$([char]0x7269)"
$target = Join-Path $desk $folder
New-Item -ItemType Directory -Force -Path $target | Out-Null
$null = & robocopy $dist $target /E /NFL /NDL /NJH /NS /NC /NP /IS /IT
if ($LASTEXITCODE -ge 8) {
    Write-Host "robocopy failed, exit code:" $LASTEXITCODE
    exit 1
}
$exe = Join-Path $target "DesktopPet.exe"
$w = New-Object -ComObject WScript.Shell
$lnk = Join-Path $desk ($folder + ".lnk")
$s = $w.CreateShortcut($lnk)
$s.TargetPath = $exe
$s.WorkingDirectory = $target
$s.Description = "桌面宠物"
$s.Save()
Write-Host "Deployed to:" $target
Write-Host "Shortcut:" $lnk
