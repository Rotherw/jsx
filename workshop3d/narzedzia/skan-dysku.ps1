<#
    Inwentaryzacja maszynerii WorkShop3D na dysku przenosnym.

    Skrypt TYLKO CZYTA. Niczego nie kopiuje, nie przenosi ani nie kasuje.

    Co robi:
      1. znajduje dysk (domyslnie F:, albo pierwszy wymienny)
      2. wyszukuje "maszyny" - foldery z punktem wejscia aplikacji
      3. liczy SHA256 plikow kodu i wskazuje dokladne duplikaty
      4. zapisuje WS3D-INWENTARZ.md (do czytania) i ws3d-inwentarz.json (dla Claude)

    Uzycie:
      .\skan-dysku.ps1
      .\skan-dysku.ps1 -Dysk "E:\"
      .\skan-dysku.ps1 -Dysk "F:\" -Wyjscie "$env:USERPROFILE\Desktop"
#>

[CmdletBinding()]
param(
    [string] $Dysk = "",
    [string] $Wyjscie = "$env:USERPROFILE\Desktop",
    [int]    $MaxGlebokosc = 6
)

$ErrorActionPreference = "Stop"

# --- 1. Znajdz dysk -------------------------------------------------------

function Znajdz-Dysk {
    param([string] $Podany)

    if ($Podany) {
        if (-not (Test-Path $Podany)) { throw "Nie widze sciezki: $Podany" }
        return (Resolve-Path $Podany).Path
    }

    if (Test-Path "F:\") { return "F:\" }

    $wymienne = Get-CimInstance Win32_LogicalDisk -Filter "DriveType = 2" |
                Sort-Object DeviceID
    if ($wymienne) { return ($wymienne[0].DeviceID + "\") }

    throw "Nie znalazlem dysku wymiennego. Podaj recznie: .\skan-dysku.ps1 -Dysk 'E:\'"
}

$korzen = Znajdz-Dysk -Podany $Dysk
Write-Host "Skanuje: $korzen" -ForegroundColor Cyan

# --- 2. Co uznajemy za "maszyne" -----------------------------------------

# Plik-znacznik => jakiego rodzaju to aplikacja.
$Znaczniki = @{
    "composer.json"    = "PHP / Laravel"
    "package.json"     = "Node / JS"
    "requirements.txt" = "Python"
    "pyproject.toml"   = "Python"
    "Pipfile"          = "Python"
    "environment.yml"  = "Python (conda)"
    "install.bat"      = "Instalator Windows"
    "start.bat"        = "Launcher Windows"
    "run.bat"          = "Launcher Windows"
    "manage.py"        = "Django"
    "artisan"          = "Laravel"
    "docker-compose.yml" = "Docker"
    "Dockerfile"       = "Docker"
    ".gitignore"       = "Repozytorium git"
}

# Rozszerzenia liczone jako kod/narzedzie (te hashujemy).
$RozszerzeniaKodu = @(
    ".py",".ps1",".bat",".cmd",".sh",".php",".js",".ts",".jsx",".tsx",
    ".html",".htm",".css",".json",".yaml",".yml",".toml",".ini",".cfg",
    ".sql",".md",".txt",".csv"
)

# Rozszerzenia traktowane jako "ladunek" - tylko liczymy, nie hashujemy.
$RozszerzeniaDanych = @(
    ".stl",".3mf",".obj",".glb",".gltf",".fbx",".blend",".lys",".chitubox",
    ".png",".jpg",".jpeg",".gif",".webp",".bmp",".tif",".tiff",".psd",
    ".mp4",".mov",".avi",".mkv",".zip",".7z",".rar",".exe",".msi",".dll",".pdf"
)

# Foldery, ktore pomijamy - smieci, nie maszyneria.
$Pomijane = @(
    "node_modules","vendor",".venv","venv","env","__pycache__",".pytest_cache",
    ".git",".idea",".vscode","System Volume Information",'$RECYCLE.BIN',
    "hf-cache",".cache","dist","build",".next"
)

function Czy-Pomijac {
    param([string] $Sciezka)
    foreach ($p in $Pomijane) {
        if ($Sciezka -match [regex]::Escape("\$p\") -or $Sciezka -match ([regex]::Escape("\$p") + '$')) {
            return $true
        }
    }
    return $false
}

# --- 3. Zbierz pliki ------------------------------------------------------

Write-Host "Zbieram liste plikow..." -ForegroundColor DarkGray

$wszystkie = Get-ChildItem -LiteralPath $korzen -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { -not (Czy-Pomijac $_.FullName) }

Write-Host ("Plikow do przejrzenia: {0}" -f $wszystkie.Count) -ForegroundColor DarkGray

# --- 4. Wykryj maszyny ----------------------------------------------------

$maszyny = @{}

foreach ($plik in $wszystkie) {
    if (-not $Znaczniki.ContainsKey($plik.Name)) { continue }

    $folder = $plik.DirectoryName
    $glebokosc = ($folder.Substring($korzen.Length) -split '\\').Count
    if ($glebokosc -gt $MaxGlebokosc) { continue }

    if (-not $maszyny.ContainsKey($folder)) {
        $maszyny[$folder] = [ordered]@{
            sciezka   = $folder
            nazwa     = Split-Path $folder -Leaf
            rodzaje   = New-Object System.Collections.Generic.List[string]
            znaczniki = New-Object System.Collections.Generic.List[string]
        }
    }
    $maszyny[$folder].znaczniki.Add($plik.Name) | Out-Null
    if (-not $maszyny[$folder].rodzaje.Contains($Znaczniki[$plik.Name])) {
        $maszyny[$folder].rodzaje.Add($Znaczniki[$plik.Name]) | Out-Null
    }
}

# Samodzielne narzedzia HTML - pojedynczy plik, ktory jest cala aplikacja.
$narzedziaHtml = $wszystkie | Where-Object {
    $_.Extension -in @(".html",".htm") -and $_.Length -gt 5KB -and $_.Length -lt 2MB
} | ForEach-Object {
    $tresc = ""
    try { $tresc = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop } catch {}
    $maSkrypt = $tresc -match '<script' 
    $maFormularz = $tresc -match '<(input|select|textarea|button)'
    if ($maSkrypt -and $maFormularz) {
        [ordered]@{
            sciezka = $_.FullName
            nazwa   = $_.Name
            rozmiar = $_.Length
            zmieniony = $_.LastWriteTime.ToString("s")
            tytul   = if ($tresc -match '<title>\s*(.*?)\s*</title>') { $Matches[1] } else { "" }
        }
    }
}

# --- 5. Statystyki i duplikaty -------------------------------------------

Write-Host "Licze sumy kontrolne plikow kodu..." -ForegroundColor DarkGray

$pliki_kodu = $wszystkie | Where-Object {
    $_.Extension.ToLower() -in $RozszerzeniaKodu -and $_.Length -lt 5MB
}

$hashe = @{}
$i = 0
foreach ($plik in $pliki_kodu) {
    $i++
    if ($i % 250 -eq 0) { Write-Host "  ...$i / $($pliki_kodu.Count)" -ForegroundColor DarkGray }
    try {
        $h = (Get-FileHash -LiteralPath $plik.FullName -Algorithm SHA256).Hash
    } catch { continue }
    if (-not $hashe.ContainsKey($h)) {
        $hashe[$h] = New-Object System.Collections.Generic.List[object]
    }
    $hashe[$h].Add([ordered]@{
        sciezka   = $plik.FullName
        nazwa     = $plik.Name
        rozmiar   = $plik.Length
        zmieniony = $plik.LastWriteTime.ToString("s")
    }) | Out-Null
}

$duplikaty = @()
foreach ($h in $hashe.Keys) {
    if ($hashe[$h].Count -gt 1) {
        $duplikaty += ,([ordered]@{
            hash  = $h
            ile   = $hashe[$h].Count
            kopie = @($hashe[$h])
        })
    }
}
$duplikaty = $duplikaty | Sort-Object { -$_.ile }

$dane = $wszystkie | Where-Object { $_.Extension.ToLower() -in $RozszerzeniaDanych }
$rozmiarDanych = ($dane | Measure-Object Length -Sum).Sum

# --- 6. Zapisz wynik ------------------------------------------------------

if (-not (Test-Path $Wyjscie)) { New-Item -ItemType Directory -Path $Wyjscie -Force | Out-Null }

$raport = [ordered]@{
    dysk           = $korzen
    data           = (Get-Date).ToString("s")
    plikow_lacznie = $wszystkie.Count
    plikow_kodu    = $pliki_kodu.Count
    plikow_danych  = $dane.Count
    rozmiar_danych_mb = [math]::Round($rozmiarDanych / 1MB, 1)
    maszyny        = @($maszyny.Values | Sort-Object { $_.sciezka })
    narzedzia_html = @($narzedziaHtml)
    duplikaty      = @($duplikaty | Select-Object -First 200)
}

$jsonSciezka = Join-Path $Wyjscie "ws3d-inwentarz.json"
$raport | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonSciezka -Encoding UTF8

$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# Inwentarz maszynerii WorkShop3D")
[void]$md.AppendLine()
[void]$md.AppendLine("Dysk: ``$korzen``  |  Skan: $($raport.data)")
[void]$md.AppendLine()
[void]$md.AppendLine("- plikow lacznie: **$($raport.plikow_lacznie)**")
[void]$md.AppendLine("- plikow kodu/narzedzi: **$($raport.plikow_kodu)**")
[void]$md.AppendLine("- plikow danych (modele, grafiki, archiwa): **$($raport.plikow_danych)** (~$($raport.rozmiar_danych_mb) MB)")
[void]$md.AppendLine()
[void]$md.AppendLine("## Znalezione aplikacje ($($raport.maszyny.Count))")
[void]$md.AppendLine()

if ($raport.maszyny.Count -eq 0) {
    [void]$md.AppendLine("_Brak - sprawdz czy podany dysk jest wlasciwy._")
} else {
    [void]$md.AppendLine("| Folder | Rodzaj | Znaczniki |")
    [void]$md.AppendLine("|---|---|---|")
    foreach ($m in $raport.maszyny) {
        $r = ($m.rodzaje -join ", ")
        $z = (($m.znaczniki | Sort-Object -Unique) -join ", ")
        [void]$md.AppendLine("| ``$($m.sciezka)`` | $r | $z |")
    }
}

[void]$md.AppendLine()
[void]$md.AppendLine("## Samodzielne narzedzia HTML ($($raport.narzedzia_html.Count))")
[void]$md.AppendLine()
if ($raport.narzedzia_html.Count -eq 0) {
    [void]$md.AppendLine("_Brak._")
} else {
    [void]$md.AppendLine("| Plik | Tytul | Rozmiar | Zmieniony |")
    [void]$md.AppendLine("|---|---|---|---|")
    foreach ($n in $raport.narzedzia_html) {
        [void]$md.AppendLine("| ``$($n.sciezka)`` | $($n.tytul) | $($n.rozmiar) B | $($n.zmieniony) |")
    }
}

[void]$md.AppendLine()
[void]$md.AppendLine("## Dokladne duplikaty ($($duplikaty.Count) grup)")
[void]$md.AppendLine()
[void]$md.AppendLine("Identyczna zawartosc (SHA256). Kandydaci do skasowania po scaleniu.")
[void]$md.AppendLine()
if ($duplikaty.Count -eq 0) {
    [void]$md.AppendLine("_Brak._")
} else {
    foreach ($d in ($duplikaty | Select-Object -First 60)) {
        [void]$md.AppendLine("**$($d.kopie[0].nazwa)** - $($d.ile) kopii, $($d.kopie[0].rozmiar) B")
        foreach ($k in $d.kopie) {
            [void]$md.AppendLine("- ``$($k.sciezka)`` _(zmieniony $($k.zmieniony))_")
        }
        [void]$md.AppendLine()
    }
    if ($duplikaty.Count -gt 60) {
        [void]$md.AppendLine("_...oraz $($duplikaty.Count - 60) dalszych grup - pelna lista w ws3d-inwentarz.json._")
    }
}

$mdSciezka = Join-Path $Wyjscie "WS3D-INWENTARZ.md"
$md.ToString() | Set-Content -LiteralPath $mdSciezka -Encoding UTF8

Write-Host ""
Write-Host "GOTOWE" -ForegroundColor Green
Write-Host "  $mdSciezka"   -ForegroundColor Green
Write-Host "  $jsonSciezka" -ForegroundColor Green
Write-Host ""
Write-Host "Wyslij te dwa pliki do Claude - na ich podstawie powstanie plan scalenia." -ForegroundColor Yellow
