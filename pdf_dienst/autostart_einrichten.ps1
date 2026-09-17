# pdf_dienst/autostart_einrichten.ps1
#
# Richtet den PDF-Dienst als Aufgabe in der Windows-Aufgabenplanung ein
# (NEU 17.09.2026) - fuer den angemeldeten Benutzer, ohne Adminrechte.
#
#   - startet bei der Anmeldung
#   - wird alle 15 Minuten erneut angestossen: Laeuft der Dienst schon,
#     beendet sich der zweite Start sofort (Mutex im Dienst). Ist er
#     abgestuerzt, laeuft er spaetestens nach 15 Minuten wieder.
#   - ohne Konsolenfenster (conhost --headless, Windows 11)
#   - keine Laufzeitgrenze (sonst beendet die Aufgabenplanung nach 72 h)
#
# PowerPoint braucht eine ANGEMELDETE Sitzung. Gesperrt (Windows+L) ist in
# Ordnung (gemessen 17.09.2026), abgemeldet nicht.
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\autostart_einrichten.ps1
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\autostart_einrichten.ps1 -Entfernen

param(
    [switch]$Entfernen,
    [string]$Skript = (Join-Path $PSScriptRoot "pdf_dienst.ps1")
)

$ErrorActionPreference = "Stop"
$Name = "FFPB PDF-Dienst"

if ($Entfernen) {
    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
        Write-Output "Aufgabe '$Name' entfernt."
    } else {
        Write-Output "Aufgabe '$Name' war nicht eingerichtet."
    }
    $stop = Join-Path $env:LOCALAPPDATA "FFPB_PDF_Dienst\stop"
    New-Item -ItemType File -Force -Path $stop | Out-Null
    Write-Output "Laufender Dienst wird ueber die Stop-Datei beendet."
    exit 0
}

if (-not (Test-Path $Skript)) { throw "Dienst-Skript nicht gefunden: $Skript" }
$Skript = (Resolve-Path $Skript).Path

$argumente = "--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Skript`""
$aktion = New-ScheduledTaskAction -Execute "conhost.exe" -Argument $argumente `
    -WorkingDirectory (Split-Path $Skript)

$benutzer = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$beiAnmeldung = New-ScheduledTaskTrigger -AtLogOn -User $benutzer
$wiederholung = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 15)

$einstellungen = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

$prinzipal = New-ScheduledTaskPrincipal -UserId $benutzer -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $Name -Action $aktion `
    -Trigger @($beiAnmeldung, $wiederholung) -Settings $einstellungen `
    -Principal $prinzipal `
    -Description "PDF-Briefkasten des FFPB Performancetools: wandelt Broschueren mit PowerPoint in PDF um. Siehe STATUS.md im Repo." `
    -Force | Out-Null

Write-Output "Aufgabe '$Name' eingerichtet fuer $benutzer."
Write-Output "Startet bei der Anmeldung und prueft alle 15 Minuten, ob der Dienst laeuft."
Write-Output "Sofort starten:  Start-ScheduledTask -TaskName '$Name'"
Write-Output "Entfernen:       ...\autostart_einrichten.ps1 -Entfernen"
