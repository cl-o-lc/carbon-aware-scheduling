# 3단계: PowerPoint로 발표 자료를 글꼴 포함 PPTX와 PDF로 저장한다 (Windows + Microsoft PowerPoint 필요).
# 사용법:  powershell -ExecutionPolicy Bypass -File scripts/09_export_deck.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$deckDir = Join-Path $root "04_발표자료"
$raw = Join-Path $deckDir "_build\deck_raw.pptx"
$name = "2026 ESD 비교과 공모전(탄소 인지 작업 스케줄링)_박수진"
$pptx = Join-Path $deckDir "$name.pptx"
$pdf = Join-Path $deckDir "$name.pdf"

$app = New-Object -ComObject PowerPoint.Application
try {
    # Open(파일, 읽기전용, 제목없음, 창표시)
    $pres = $app.Presentations.Open($raw, -1, 0, 0)
    # 24 = ppSaveAsOpenXMLPresentation, -1 = 글꼴 포함(EmbedTrueTypeFonts)
    $pres.SaveAs($pptx, 24, -1)
    # 32 = ppSaveAsPDF
    $pres.SaveAs($pdf, 32)
    $pres.Close()
} finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
Write-Output "PPTX: $pptx"
Write-Output "PDF : $pdf"
