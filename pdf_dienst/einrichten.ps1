# pdf_dienst/einrichten.ps1
#
# Einmalige Einrichtung des PDF-Dienstes auf dem Buero-PC (NEU 17.09.2026).
#
# Liest den GitHub-Schluessel "pdf-briefkasten-pc" aus einer Textdatei,
# verschluesselt ihn mit DPAPI unter dem angemeldeten Windows-Konto und
# LOESCHT die Textdatei. Den verschluesselten Schluessel kann nur dieses
# Konto auf diesem PC wieder lesen.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\einrichten.ps1
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\einrichten.ps1 -TokenDatei C:\pfad\token.txt
#
# Schluessel erneuern (Frist siehe STATUS.md): neuen Schluessel in die
# Textdatei, dieses Skript erneut ausfuehren, Dienst neu starten.

param(
    [string]$TokenDatei = "C:\Entwicklung\pdf_briefkasten_pc_token.txt"
)

$ErrorActionPreference = "Stop"
$Ordner = Join-Path $env:LOCALAPPDATA "FFPB_PDF_Dienst"
$Ziel = Join-Path $Ordner "token.dat"

if (-not (Test-Path $TokenDatei)) {
    throw "Schluesseldatei nicht gefunden: $TokenDatei"
}
$token = (Get-Content -Raw -Path $TokenDatei).Trim()
if (-not $token.StartsWith("github_pat_")) {
    throw "Die Datei enthaelt keinen fine-grained GitHub-Schluessel (github_pat_...)."
}

New-Item -ItemType Directory -Force -Path $Ordner | Out-Null
$sicher = ConvertTo-SecureString -String $token -AsPlainText -Force
ConvertFrom-SecureString -SecureString $sicher | Set-Content -Path $Ziel -Encoding ASCII

# Gegenprobe, bevor die Klartextdatei verschwindet
$zurueck = Get-Content -Path $Ziel | ConvertTo-SecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($zurueck)
try {
    $klar = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ($klar -ne $token) {
    throw "Gegenprobe fehlgeschlagen - Klartextdatei bleibt liegen."
}

Remove-Item -Path $TokenDatei -Force
Write-Output "Schluessel verschluesselt abgelegt: $Ziel"
Write-Output "Klartextdatei geloescht: $TokenDatei"
