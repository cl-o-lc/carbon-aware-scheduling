# 3단계: PowerPoint로 발표 자료를 글꼴 포함 PPTX와 PDF로 저장한다 (Windows + Microsoft PowerPoint 필요).
# 사용법:  powershell -ExecutionPolicy Bypass -File scripts/09_export_deck.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$deckDir = Join-Path $root "04_발표자료"
$raw = Join-Path $deckDir "_build\deck_raw.pptx"
$name = "2026 ESD 비교과 공모전(탄소 인지 작업 스케줄링)_박수진"
$pptx = Join-Path $deckDir "$name.pptx"
$pdf = Join-Path $deckDir "$name.pdf"

# 결과 파일이 다른 프로그램에서 열려 있으면 아무것도 건드리지 않고 멈춘다
foreach ($f in @($pptx, $pdf)) {
    if (Test-Path $f) {
        try { $s = [System.IO.File]::Open($f, 'Open', 'ReadWrite', 'None'); $s.Close() }
        catch { Write-Output "[중단] 파일이 열려 있습니다. 닫은 뒤 다시 실행하세요: $f"; exit 1 }
    }
}

# 이미 실행 중인 PowerPoint(사용자 창)는 끝나도 닫지 않는다
$wasRunning = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app = New-Object -ComObject PowerPoint.Application
$pres = $null
try {
    # Open(파일, 읽기전용, 제목없음, 창표시)
    $pres = $app.Presentations.Open($raw, -1, 0, 0)
    # 24 = ppSaveAsOpenXMLPresentation, -1 = 글꼴 포함(EmbedTrueTypeFonts)
    $pres.SaveAs($pptx, 24, -1)
    # 32 = ppSaveAsPDF
    $pres.SaveAs($pdf, 32)
} finally {
    if ($pres) { $pres.Close() }
    if (-not $wasRunning) { $app.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
Write-Output "PPTX: $pptx"
Write-Output "PDF : $pdf"
