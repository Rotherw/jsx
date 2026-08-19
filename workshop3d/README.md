# Maszyneria WorkShop3D

Docelowo **jeden folder** na wszystkie narzędzia WS3D, zamiast plików
porozrzucanych po dysku przenośnym, Drive i korzeniu repozytorium.

Dokument wiążący dla całości: **[`SYSTEM.md`](SYSTEM.md)** — System Operacyjny v2.0.
Gdy kod rozejdzie się z tym dokumentem, rację ma dokument.

## Stan na dziś

| Maszyna | Co robi | Gdzie teraz leży | Status |
|---|---|---|---|
| **KF2 Studio** | generator artykułów wiki + generator sesji + rejestr modeli i listingi | `kf2_studio/` | ✅ scalone (PR #8) |
| **WorkShop3D Publisher** | automatyczna publikacja modeli na sklepy i social media | `workshop3d_publisher/` **+ kopia na Drive** | ⏸ do porównania wersji |
| **Generator obrazów (SD 1.5)** | Stable Diffusion w przeglądarce | `app.py` + `start.bat` w korzeniu repo | ⏸ do przeniesienia |
| **Meshy PNG Generator** | obrazy referencyjne pod MeshyAI Image-to-3D (Faza 1) | Drive, **co najmniej 3 kopie** | ⏸ do rozstrzygnięcia, która wiodąca |
| **Segregator Commander V3** | paczkuje produkt wg struktury 00–10 | dysk lokalny / `F:` | ❓ kodu jeszcze nie widziałem |
| **Landing WorkShop3D** | witryna spinająca sklepy i social media | Drive: „WorkShop3D - Witryna na figurki v1" | ❓ nierozpoznane |
| **Wiki.js** | prawdopodobnie silnik wiki.kf2.pl | skrót `.lnk` na Drive | ❓ nierozpoznane |

## Co dał skan Drive'a (19.08.2026)

Folder `APLIKACJE` zawiera cztery aplikacje i sporo balastu.

**Aplikacje:** `Generator Obrazu WorkShop3D` (→ `Workshop3D_Meshy_PNG_Generator`),
`WorkShop3D` (`_zips`, `Assets`), `WorkShop3D-Meshy-PNG-Generator_2`
(→ `WorkShop3D-Meshy-PNG-Generator`: `app.py` 11 459 B, `start.bat`,
`requirements.txt`, `README.txt`, `env/`, `fix_v13.py`, `fix_pl.py`,
`test_api.py`), `Doku.Ws3d` (dokumentacja systemu + eksporty CSV).

**Do posprzątania:**

- generator sesji KF2 w **pięciu identycznych kopiach** po 27 119 B
  (korzeń Drive'a, `KF2/`, oraz trzy w `APLIKACJE/`) — wszystkie już scalone
  w `kf2_studio/`, więc to czysta lista do skasowania,
- generator wiki KF2 w dwóch kopiach po 28 676 B — jak wyżej,
- notatki systemowe v1 w dwóch identycznych kopiach po 29 668 B
  — zastąpione przez [`SYSTEM.md`](SYSTEM.md),
- `GitHubDesktopSetup-x64.msi` **i** `.exe` (po ~308 MB) — ten sam instalator
  dwa razy, plus `blender-5.2.0-windows-x64.msi` (365 MB). Razem ~982 MB
  cudzego softu, który pobiera się ze strony producenta w minutę,
- środowiska wirtualne i `__pycache__` — dziesiątki tysięcy plików, które
  odtwarza jedna komenda `pip install`. Zaśmiecają Drive i zalewają
  wyszukiwanie,
- siedem skrótów `.lnk` — poza jednym komputerem bezużyteczne.

## Adresy z systemu v2.0

Główny obszar roboczy i magazyn źródeł są na dysku **C:**, nie na przenośnym:

```
C:\Users\RafałKarwowski\WorkShop3D\WorkShop3D
C:\Users\RafałKarwowski\WorkShop3D\WorkShop3D\Segregator\MAGAZYN
```

Dysk `F:` to miejsce, gdzie **instaluje się Publisher** — `1_ZAINSTALUJ.bat`
kieruje instalację do `F:\WorkShop3D_Publisher`, jeśli dysk jest podpięty.
To dwie różne rzeczy: aplikacje na `F:`, materiał roboczy na `C:`.

## Krok 1 — inwentaryzacja dysku (wciąż aktualne)

Skan Drive'a pokazał, co zostało wgrane, ale nie mówi, co jeszcze siedzi
na dysku i **która kopia jest najnowsza**. To rozstrzyga skaner:

```
workshop3d\narzedzia\SKANUJ-DYSK.bat
```

Skrypt **tylko czyta**. Wykrywa aplikacje po punktach wejścia, samodzielne
narzędzia HTML, dokładne duplikaty po SHA256 oraz ładunek danych. Wynik:
`WS3D-INWENTARZ.md` + `ws3d-inwentarz.json` na Pulpicie.

Inny dysk niż `F:`:

```powershell
powershell -ExecutionPolicy Bypass -File .\skan-dysku.ps1 -Dysk "E:\"
```

## Krok 2 — docelowy układ

```
workshop3d/
  SYSTEM.md           dokument wiążący (v2.0)
  kf2-studio/         wiki + sesje + rejestr modeli i listingi
  publisher/          publikacja na sklepy i social media
  generator-obrazow/  Stable Diffusion w przeglądarce
  generator-meshy/    obrazy referencyjne pod MeshyAI (Faza 1)
  segregator/         paczkowanie produktu wg struktury 00–10
  landing/            witryna spinająca sklepy i social media
  narzedzia/          skrypty pomocnicze (m.in. skaner dysku)
  README.md           ta mapa
```

Zasady scalania — zgodne z sekcją 5 systemu:

1. **Jedna kopia każdego narzędzia.** Duplikaty z inwentarza znikają,
   zostaje najnowsza wersja.
2. **Oryginały nie są usuwane przed potwierdzeniem.** Przeniesienie idzie
   przez git, więc każdy krok da się cofnąć.
3. **Launchery zostają tam, gdzie były.** `1_ZAINSTALUJ.bat` i `start.bat`
   w korzeniu repo pozostają jako cienkie skróty do nowych lokalizacji —
   skróty na pulpicie mają dalej działać.
4. **Środowiska i cache nie wchodzą do repo.** `env/`, `__pycache__`,
   `_vendor`, `node_modules` odtwarza instalacja.

## Krok 3 — sprzątanie źródeł

Dopiero po potwierdzeniu, że scalona wersja działa, kasujemy rozrzucone kopie
z dysku i Drive'a. Nie wcześniej.
