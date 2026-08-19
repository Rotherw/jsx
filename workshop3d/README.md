# Maszyneria WorkShop3D

Docelowo **jeden folder** na wszystkie narzędzia WS3D, zamiast plików
porozrzucanych po dysku przenośnym, Drive i korzeniu repozytorium.

## Stan na dziś

| Maszyna | Co robi | Gdzie teraz leży | Status |
|---|---|---|---|
| **KF2 Studio** | generator artykułów wiki + generator sesji + panel listingów | `kf2_studio/` | ✅ scalone (PR #8) |
| **WorkShop3D Publisher** | automatyczna publikacja modeli na sklepy i social media | `workshop3d_publisher/` | ⏸ czeka na inwentarz |
| **Generator obrazów** | Stable Diffusion 1.5 w przeglądarce | `app.py` + `start.bat` w korzeniu repo | ⏸ czeka na inwentarz |
| **Segregator Commander V3** | porządkowanie modeli STL (desktop, tkinter) | dysk przenośny `F:\` | ❓ nierozpoznane |
| **Landing WorkShop3D** | witryna spinająca sklepy i social media | Drive: „WorkShop3D - Witryna na figurki v1" | ❓ nierozpoznane |
| _reszta_ | ? | dysk przenośny `F:\` | ❓ nierozpoznane |

## Dlaczego to jeszcze nie jest scalone

Dysk przenośny (`F:\`) nie jest dostępny z sesji Claude Code — ta sesja
działa w kontenerze w chmurze, a dysk jest wpięty do komputera w warsztacie.
Przeniesienie czegokolwiek przed poznaniem zawartości dysku groziłoby
utrwaleniem starszej kopii aplikacji zamiast nowszej — a wiadomo już, że
kopie się dublują (dwa identyczne pliki `KF2-Generator-Sesji.html`,
dwie identyczne notatki wdrożeniowe na Drive).

Że dysk to `F:\` wiadomo z `1_ZAINSTALUJ.bat`, który instaluje Publishera
do `F:\WorkShop3D_Publisher`, jeśli dysk jest podpięty.

## Krok 1 — inwentaryzacja (do wykonania na komputerze z dyskiem)

Podepnij dysk i kliknij dwukrotnie:

```
workshop3d\narzedzia\SKANUJ-DYSK.bat
```

Skrypt **tylko czyta**. Nic nie kopiuje, nie przenosi ani nie kasuje.

Na Pulpicie pojawią się dwa pliki:

- `WS3D-INWENTARZ.md` — do przejrzenia okiem
- `ws3d-inwentarz.json` — do wysłania Claude

Co skrypt wykrywa:

- **aplikacje** — foldery z punktem wejścia (`composer.json`, `package.json`,
  `requirements.txt`, `install.bat`, `artisan`, `Dockerfile`, `.git`…)
- **samodzielne narzędzia HTML** — pojedynczy plik będący całą aplikacją,
  jak oba generatory KF2
- **dokładne duplikaty** — identyczna zawartość (SHA256), czyli te same
  narzędzia w kilku kopiach; to jest lista do posprzątania
- **ładunek danych** — modele STL/3MF, grafiki, archiwa: liczone, ale nie
  hashowane, żeby skan nie trwał godzinami

Inny dysk niż `F:`:

```powershell
powershell -ExecutionPolicy Bypass -File .\skan-dysku.ps1 -Dysk "E:\"
```

## Krok 2 — scalenie (po inwentarzu)

Mając inwentarz, wiadomo która kopia każdej aplikacji jest najnowsza
i co w ogóle istnieje. Wtedy powstaje docelowy układ:

```
workshop3d/
  kf2-studio/         generatory wiki + sesje + listingi (Laravel)
  publisher/          automatyczna publikacja na sklepy i social media
  generator-obrazow/  Stable Diffusion w przeglądarce
  segregator/         porządkowanie modeli STL
  landing/            witryna spinająca sklepy i social media
  narzedzia/          skrypty pomocnicze (m.in. ten skaner)
  README.md           ta mapa
```

Zasady scalania:

1. **Jedna kopia każdego narzędzia.** Duplikaty z inwentarza znikają,
   zostaje najnowsza wersja.
2. **Launchery zostają tam, gdzie były.** `1_ZAINSTALUJ.bat` i `start.bat`
   w korzeniu repo pozostają jako cienkie skróty do nowych lokalizacji —
   nawyk kliknięcia i skróty na pulpicie mają dalej działać.
3. **Nic nie ginie przed potwierdzeniem.** Przeniesienie idzie przez git,
   więc każdy krok da się cofnąć.

## Krok 3 — sprzątanie źródeł

Dopiero po potwierdzeniu, że scalona wersja działa, kasujemy rozrzucone
kopie z dysku i Drive'a. Nie wcześniej.
