# pdf_dienst/pdf_dienst.ps1
#
# PDF-Dienst fuer den PDF-Briefkasten (NEU 17.09.2026).
#
# WARUM: Die Broschuere soll als PDF so aussehen wie "Speichern unter -> PDF"
# in Desktop-PowerPoint. Auf Streamlit Cloud gibt es kein PowerPoint. Dieser
# Dienst laeuft auf einem angemeldeten Buero-PC mit Office, holt Auftraege aus
# dem privaten Repo FFPBAM/pdf-briefkasten (Release "auftraege"), wandelt sie
# mit PowerPoint um und legt das PDF zurueck. Gegenstueck in der App:
# modules/pdf_briefkasten.py - die Dateinamen sind das Protokoll.
#
#   <auftrag>.pptx         App -> Dienst
#   <auftrag>.pdf          Dienst -> App
#   <auftrag>.fehler.txt   Dienst -> App, wenn die Umwandlung scheitert
#   lebenszeichen-<unixzeit>.txt   jede Minute, damit die App weiss, ob jemand da ist
#
# Voraussetzung: einmal pdf_dienst\einrichten.ps1 ausgefuehrt (Schluessel per DPAPI).
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\pdf_dienst.ps1
#   powershell -ExecutionPolicy Bypass -File pdf_dienst\pdf_dienst.ps1 -LaufzeitMinuten 20
#
# Beenden: Datei %LOCALAPPDATA%\FFPB_PDF_Dienst\stop anlegen (wird beim
# Beenden entfernt) oder den Prozess beenden.
#
# POWERPOINT DES NUTZERS: PowerPoint laeuft pro Sitzung nur einmal. Ist es
# offen, haengt sich der Dienst an DIESELBE Instanz. Deshalb wird nur die
# eigene Praesentation geschlossen und PowerPoint nur beendet, wenn es
# unsichtbar ist und keine Praesentation mehr offen hat - also nie das
# PowerPoint, mit dem gerade jemand arbeitet.

param(
    [string]$Repo = "FFPBAM/pdf-briefkasten",
    [int]$AbfrageSekunden = 5,
    [int]$LebenszeichenSekunden = 60,
    [int]$LaufzeitMinuten = 0
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Ordner = Join-Path $env:LOCALAPPDATA "FFPB_PDF_Dienst"
$Arbeit = Join-Path $Ordner "arbeit"
$Log = Join-Path $Ordner "dienst.log"
$StopDatei = Join-Path $Ordner "stop"
$ReleaseTag = "auftraege"
$AuftragMuster = '^(\d{8}-\d{6}-[0-9a-f]{8})\.pptx$'
$VerwaistNachMinuten = 30

New-Item -ItemType Directory -Force -Path $Arbeit | Out-Null

function Schreibe-Log([string]$text) {
    if ((Test-Path $Log) -and (Get-Item $Log).Length -gt 1MB) {
        Move-Item -Force $Log "$Log.alt"
    }
    $zeile = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $text
    Add-Content -Path $Log -Value $zeile -Encoding UTF8
    Write-Output $zeile
}

function Lies-Token {
    $dat = Join-Path $Ordner "token.dat"
    if (-not (Test-Path $dat)) { throw "Kein Schluessel - zuerst pdf_dienst\einrichten.ps1 ausfuehren." }
    $sicher = Get-Content -Path $dat | ConvertTo-SecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sicher)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

$Token = Lies-Token
$Kopf = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "ffpb-pdf-dienst"
}

function Api([string]$methode, [string]$url) {
    return Invoke-RestMethod -Method $methode -Uri $url -Headers $Kopf -TimeoutSec 60
}

function Hole-ReleaseId {
    try {
        return (Api "GET" "https://api.github.com/repos/$Repo/releases/tags/$ReleaseTag").id
    } catch {
        $koerper = @{ tag_name = $ReleaseTag; name = "PDF-Auftraege (Ablage, nicht loeschen)";
                      body = "Ablage des PDF-Briefkastens. Anhaenge kommen und gehen automatisch." } | ConvertTo-Json
        return (Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$Repo/releases" `
                -Headers $Kopf -Body $koerper -ContentType "application/json" -TimeoutSec 60).id
    }
}

# Bedingte Abfrage (ETag): Hat sich an der Liste nichts geaendert, antwortet
# GitHub mit 304 - und 304-Antworten zaehlen NICHT gegen das Anfragelimit.
# Damit kostet das Warten auf Auftraege praktisch nichts, auch alle 5 s.
$script:AnhaengeEtag = $null
$script:AnhaengeListe = @()
$script:Erledigt = @{}   # Anhang-Ids, die dieser Dienst schon abgeholt hat

function Anhaenge($rid) {
    $req = [Net.HttpWebRequest]::Create("https://api.github.com/repos/$Repo/releases/$rid/assets?per_page=100")
    $req.Headers.Add("Authorization", "Bearer $Token")
    $req.Headers.Add("X-GitHub-Api-Version", "2022-11-28")
    $req.Accept = "application/vnd.github+json"
    $req.UserAgent = "ffpb-pdf-dienst"
    $req.Timeout = 60000
    if ($script:AnhaengeEtag) { $req.Headers.Add("If-None-Match", $script:AnhaengeEtag) }
    try {
        $antwort = $req.GetResponse()
    } catch [Net.WebException] {
        $r = $_.Exception.Response
        if ($r -and [int]$r.StatusCode -eq 304) { $r.Close(); return $script:AnhaengeListe }
        throw
    }
    try {
        $leser = New-Object IO.StreamReader($antwort.GetResponseStream(), [Text.Encoding]::UTF8)
        $daten = ConvertFrom-Json $leser.ReadToEnd()
        # ForEach-Object zaehlt das Feld auf - ConvertFrom-Json liefert es in
        # PowerShell 5.1 sonst als EIN Objekt.
        $script:AnhaengeListe = @($daten | ForEach-Object { $_ })
        $script:AnhaengeEtag = $antwort.Headers["ETag"]
        return $script:AnhaengeListe
    } finally { $antwort.Close() }
}

function Lade-Hoch($rid, [string]$name, [string]$pfad, [string]$typ) {
    $url = "https://uploads.github.com/repos/$Repo/releases/$rid/assets?name=" + [Uri]::EscapeDataString($name)
    Invoke-RestMethod -Method Post -Uri $url -Headers $Kopf -InFile $pfad -ContentType $typ -TimeoutSec 120 | Out-Null
}

function Loesche-Anhang($id) {
    try {
        Invoke-RestMethod -Method Delete -Uri "https://api.github.com/repos/$Repo/releases/assets/$id" -Headers $Kopf -TimeoutSec 60 | Out-Null
    } catch [Net.WebException] {
        # 404 = schon weg (z.B. von der App aufgeraeumt) - Ziel erreicht.
        $r = $_.Exception.Response
        if (-not ($r -and [int]$r.StatusCode -eq 404)) { throw }
    }
}

function Lade-Herunter($id, [string]$ziel) {
    # Der Anhang leitet auf eine signierte Speicher-URL um. Die Weiterleitung
    # selbst ausfuehren und dort OHNE Schluessel abrufen.
    $req = [Net.HttpWebRequest]::Create("https://api.github.com/repos/$Repo/releases/assets/$id")
    $req.AllowAutoRedirect = $false
    $req.Headers.Add("Authorization", "Bearer $Token")
    $req.Accept = "application/octet-stream"
    $req.UserAgent = "ffpb-pdf-dienst"
    $req.Timeout = 60000
    $antwort = $req.GetResponse()
    try {
        $code = [int]$antwort.StatusCode
        if ($code -ge 300 -and $code -lt 400) {
            $weiter = $antwort.Headers["Location"]
            (New-Object Net.WebClient).DownloadFile($weiter, $ziel)
        } else {
            $strom = $antwort.GetResponseStream()
            $datei = [IO.File]::Create($ziel)
            try { $strom.CopyTo($datei) } finally { $datei.Close(); $strom.Close() }
        }
    } finally { $antwort.Close() }
}

function Wandle-Um([string]$pptx, [string]$pdf) {
    $ppt = New-Object -ComObject PowerPoint.Application
    $pres = $null
    try {
        # ReadOnly, ohne Titel-Aenderung, OHNE Fenster
        $pres = $ppt.Presentations.Open($pptx, $true, $false, $false)
        $pres.SaveAs($pdf, 32)   # 32 = ppSaveAsPDF
    } finally {
        if ($pres) { $pres.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($pres) }
        if ($ppt.Presentations.Count -eq 0 -and $ppt.Visible -eq 0) { $ppt.Quit() }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ppt)
        [GC]::Collect(); [GC]::WaitForPendingFinalizers()
    }
}

function Sende-Lebenszeichen($rid, $liste) {
    # NICHT Get-Date -UFormat %s: das rechnet in Windows PowerShell 5.1 mit
    # der Ortszeit und laege damit ein bis zwei Stunden daneben.
    $unix = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $name = "lebenszeichen-$unix.txt"
    $pfad = Join-Path $Arbeit $name
    Set-Content -Path $pfad -Value ("{0} {1:yyyy-MM-dd HH:mm:ss}" -f $env:COMPUTERNAME, (Get-Date)) -Encoding ASCII
    try { Lade-Hoch $rid $name $pfad "text/plain" } finally { Remove-Item -Force $pfad }
    foreach ($a in $liste) {
        if ($a.name -like "lebenszeichen-*.txt" -and $a.name -ne $name) { Loesche-Anhang $a.id }
    }
}

# Nur EIN Dienst je PC - zwei wuerden denselben Auftrag doppelt bearbeiten.
$mutex = New-Object Threading.Mutex($false, "Local\FFPB_PDF_Dienst")
if (-not $mutex.WaitOne(0)) {
    Write-Output "PDF-Dienst laeuft bereits - beende."
    exit 0
}

try {
    Remove-Item -Force -ErrorAction SilentlyContinue $StopDatei
    $rid = Hole-ReleaseId
    Schreibe-Log "Dienst gestartet (Repo $Repo, Release $rid, Abfrage alle $AbfrageSekunden s)"
    $start = Get-Date
    $letztesLebenszeichen = [datetime]::MinValue

    while ($true) {
        if (Test-Path $StopDatei) { Schreibe-Log "Stop-Datei gefunden - beende."; break }
        if ($LaufzeitMinuten -gt 0 -and ((Get-Date) - $start).TotalMinutes -ge $LaufzeitMinuten) {
            Schreibe-Log "Laufzeit $LaufzeitMinuten min erreicht - beende."; break
        }
        try {
            $liste = Anhaenge $rid

            if (((Get-Date) - $letztesLebenszeichen).TotalSeconds -ge $LebenszeichenSekunden) {
                Sende-Lebenszeichen $rid $liste
                $letztesLebenszeichen = Get-Date
            }

            foreach ($a in $liste) {
                $m = [regex]::Match($a.name, $AuftragMuster)
                if (-not $m.Success) { continue }
                # GitHub listet einen Anhang schon WAEHREND des Hochladens
                # (state "starter"); herunterladen geht erst bei "uploaded".
                # Ohne diese Zeile: 404 bei grossen Broschueren (17.09.2026).
                if ($a.state -ne "uploaded") { continue }
                # Schon abgeholt? Eine (per ETag zwischengespeicherte oder von
                # GitHub verzoegert aktualisierte) Liste kann ihn noch fuehren.
                if ($script:Erledigt.ContainsKey([string]$a.id)) { continue }
                $script:Erledigt[[string]$a.id] = Get-Date
                $auftrag = $m.Groups[1].Value
                $pptx = Join-Path $Arbeit "$auftrag.pptx"
                $pdf = Join-Path $Arbeit "$auftrag.pdf"
                $t0 = Get-Date
                try {
                    Lade-Herunter $a.id $pptx
                    Loesche-Anhang $a.id          # abgeholt - kein zweiter Durchlauf
                    $t1 = Get-Date
                    Wandle-Um $pptx $pdf
                    $t2 = Get-Date
                    Lade-Hoch $rid "$auftrag.pdf" $pdf "application/pdf"
                    $t3 = Get-Date
                    Schreibe-Log ("{0}: {1:N1} MB -> PDF {2:N1} MB | holen {3:N1} s, umwandeln {4:N1} s, zurueck {5:N1} s" -f `
                        $auftrag, ($a.size / 1MB), ((Get-Item $pdf).Length / 1MB),
                        ($t1 - $t0).TotalSeconds, ($t2 - $t1).TotalSeconds, ($t3 - $t2).TotalSeconds)
                } catch {
                    $grund = $_.Exception.Message
                    Schreibe-Log "${auftrag}: FEHLER $grund"
                    $fehlerPfad = Join-Path $Arbeit "$auftrag.fehler.txt"
                    Set-Content -Path $fehlerPfad -Value $grund -Encoding UTF8
                    try { Lade-Hoch $rid "$auftrag.fehler.txt" $fehlerPfad "text/plain" } catch { }
                    Remove-Item -Force -ErrorAction SilentlyContinue $fehlerPfad
                } finally {
                    Remove-Item -Force -ErrorAction SilentlyContinue $pptx, $pdf
                }
            }

            # Verwaiste Dateien (App hat nicht abgeholt) nach 30 min entfernen
            foreach ($a in $liste) {
                if ($a.name -like "lebenszeichen-*") { continue }
                if ($script:Erledigt.ContainsKey([string]$a.id)) { continue }
                $alter = ((Get-Date).ToUniversalTime() - ([datetime]$a.created_at).ToUniversalTime()).TotalMinutes
                if ($alter -gt $VerwaistNachMinuten) {
                    $script:Erledigt[[string]$a.id] = Get-Date
                    Loesche-Anhang $a.id
                    Schreibe-Log ("verwaist entfernt: {0} ({1:N0} min alt)" -f $a.name, $alter)
                }
            }

            # Gedaechtnis der abgeholten Ids klein halten (2 h reichen weit)
            foreach ($k in @($script:Erledigt.Keys)) {
                if (((Get-Date) - $script:Erledigt[$k]).TotalHours -gt 2) { $script:Erledigt.Remove($k) }
            }
        } catch {
            Schreibe-Log "Abfrage fehlgeschlagen: $($_.Exception.Message)"
            Start-Sleep -Seconds 30
        }
        Start-Sleep -Seconds $AbfrageSekunden
    }
} finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $StopDatei
    $mutex.ReleaseMutex()
}
