# KF2 Studio

Jedno narzędzie webowe zamiast luźnych plików HTML rozrzuconych po Google Drive.
Laravel 12 + PostgreSQL. Trzy moduły w jednym miejscu:

| Moduł | Co zastępuje | Stan |
|---|---|---|
| **Wiki** | `KF2-Wiki-Generator-Artykulow.html` | pełny port |
| **Sesje** | `KF2-Generator-Sesji.html` | pełny port + odtwarzalne ziarno |
| **Listingi** | planowany „listing generator” | centralna baza + eksport per platforma |

## Skąd wzięły się dane

Kanon, szkielety artykułów i słowniki generatora sesji zostały wyciągnięte
1:1 z dwóch oryginalnych plików na Drive:

- `KF2-Wiki-Generator-Artykulow.html` — id `14sXZPHj-iEj20zLLird0WJ_JdBLCoBdt`
- `KF2-Generator-Sesji.html` — id `1IozFESQ8SyiSGuSOiCqT7ZtsLf8DrAoi`
  (**oraz identyczna kopia w korzeniu Drive**, id `1jtQtK0rQa9BEZqjl3iVXXoCEgm4IABOV`
  — ta sama zawartość, 27 119 bajtów; to jest ta „luźna kopia do posprzątania”)

Wszystko wylądowało w `database/data/*.php`, a stamtąd seederami do bazy.
Po zweryfikowaniu, że aplikacja daje te same wyniki, oryginały na Drive można
zarchiwizować — kanon nie żyje już w plikach HTML.

## Uruchomienie

```bash
composer install
cp .env.example .env
php artisan key:generate

createdb kf2_studio            # albo: DB_CONNECTION=sqlite w .env
php artisan migrate --seed

php artisan serve
```

Bez Postgresa da się odpalić od ręki: ustaw `DB_CONNECTION=sqlite` w `.env`
i `touch database/kf2.sqlite`.

## Testy

Rdzeń generatorów (`app/Domain/`) nie zależy od Laravela, więc da się go
sprawdzić bez instalowania czegokolwiek:

```bash
php tools/smoke.php     # 58 asercji, samo PHP
```

Pełny zestaw po `composer install`:

```bash
vendor/bin/phpunit
php artisan kf2:smoke
```

## Jak to jest zbudowane

```
app/Domain/            czysty PHP, zero Laravela — logika generatorów
  Template.php         silnik szablonów ({pole}, {@luka}, [[warunek?a||b]])
  WikiGenerator.php    artykuły wiki
  SessionGenerator.php szkielety sesji
  Losowanie.php        deterministyczny losownik (ziarno)
  Listing/             eksport i kontrola spójności listingów
app/Support/Kanon.php  czyta dane z bazy, spada na pliki gdy baza pusta
database/data/         źródło prawdy dla seederów
```

Podział jest celowy: dane domenowe siedzą w bazie i da się je edytować bez
wdrożenia kodu, a logika jest testowalna bez bazy.

### Moduł Wiki

Dziewięć typów artykułów (lokacja, państwo, rasa, postać, wydarzenie,
organizacja, bóstwo, bestia, artefakt). Każdy ma własny zestaw pól i szkielet
sekcji. Obowiązuje **zasada zero-wymyślania**: czego nie podasz, generator
oznacza jako `[UZUPEŁNIJ: ...]` zamiast zmyślać kanon.

### Moduł Sesje

Rodzaj (FG / prywatna), skala, do dwóch motywów, państwo, miejsce, frakcja,
długość, ton, powiązanie z Wieściami. Sesje FG dostają automatycznie notkę
o wymogu zgodności z kanonem.

Różnica względem wersji HTML: **każdy wynik ma ziarno**. To samo ziarno i te
same wejścia zawsze dają ten sam szkielet, więc zapisana sesja jest odtwarzalna,
a nie tylko przechowana jako tekst.

### Moduł Listingi — rejestr modeli

Odwzorowuje **sekcję 7** dokumentu [`../workshop3d/SYSTEM.md`](../workshop3d/SYSTEM.md):
jeden wpis rejestru z podziałem na Tożsamość / Świat / Produkcja / Sprzedaż /
Dystrybucja, ze statusami `SOURCE → IN_PROGRESS → READY_TO_UPLOAD → UPLOADED →
PUBLISHED → NEEDS_UPDATE → ARCHIVED`. SKU jest niezmienne po nadaniu —
model rzuca wyjątkiem przy próbie zmiany.

Z jednego wpisu wyliczane są teksty pod platformy w kolejności z sekcji 13:
**Cults3D → Thangs → Creality Cloud EU → Creality Cloud CN**. Pozostałe
(MyMiniFactory, Printables, MakerWorld, 3DExport, Threeding) tylko na osobne
polecenie. Creality CN dostaje osobno redagowany opis, nie tłumaczenie.

`ListingExporter::plikiPaczki()` składa komplet plików katalogu
`06_THANGS_LISTING` z paczki Commander V3 (sekcja 6) — do pobrania jako zip
i wypakowania wprost do folderu produktu.

`ListingLinter` realizuje maszynowo sprawdzalne pozycje checklisty z sekcji 14.
Uwagi mają wagę `blokuje` albo `uwaga`:

| Reguła | Waga |
|---|---|
| literówka w nazwie marki (`WorShop3D`, `Workshop 3D`, zły rozkład wielkich liter) | blokuje |
| urwany link kończący się na `@` lub separatorze | blokuje |
| prefiks `KF2` przy produkcie, który nie jest KF2 | blokuje |
| produkt KF2 bez źródła lore (sekcja 10) | blokuje |
| deklaracja „supportless" / „print tested" bez potwierdzenia w rejestrze | blokuje |
| brak licencji podstawowej (sekcja 11) | blokuje |
| status `PUBLISHED`/`UPLOADED` bez zapisanego linku (sekcja 13) | blokuje |
| „Kufel i Kości" przy produkcie z innej kolekcji | blokuje |
| tytuł poza wzorcem `KF2 [Name] - [Descriptor] - WorkShop3D` | uwaga |
| „Chibi" w tytule sprzedażowym | uwaga |
| brak nazwy albo opisu w jednym z języków | uwaga |
| powtórzony tag | uwaga |
| licencja komercyjna bez wpisanego limitu sprzedaży | uwaga |

Osobno `sprawdzNazwePliku()` pilnuje reguł z sekcji 8: ASCII, bez polskich
znaków, podkreślniki zamiast spacji, bez nazw typu `final_final2`.

Limity znaków platform mają flagę `limity_potwierdzone` — dopóki jest `false`,
aplikacja pokazuje limit jako orientacyjny i dokłada ostrzeżenie do eksportu.
Sekcja 13 zabrania opierać się ślepo na starych limitach tagów, więc popraw je
w tabeli `platformy` po pierwszym realnym wystawieniu.

## Zmiany względem oryginałów

Świadome odstępstwa, nie przypadki:

1. **Polskie znaki diakrytyczne.** Oryginały pisały „Polozenie”, „Panstwo”.
   Baza i widoki są w UTF-8, więc teksty mają pełną polszczyznę.
2. **Ziarno w generatorze sesji** — patrz wyżej.
3. **Pole „Rok / data” w typie „Postać”** było w oryginale widoczne, ale nigdy
   nie trafiało do wyniku. Teraz ląduje w Karcie postaci jako „Wzmiankowany”.
4. **Ukryte pola nie przeciekają.** Wartość pola niewidocznego dla danego typu
   jest odrzucana po stronie serwera, nie tylko chowana w UI.
