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

### Moduł Listingi

Jeden rekord produktu (tytuł PL/EN, opis PL/EN, tagi) → wyliczany eksport pod
Thangs, Cults3D, Creality Cloud CN i INT, MyMiniFactory oraz Printables.
Eksporter przycina do limitów, normalizuje tagi i usuwa to, czego dana
platforma nie przyjmuje (np. linki zewnętrzne w wersji CN).

`ListingLinter` sprawdza przed publikacją:

- literówki w nazwie marki (`WorShop3D`, `Workshop 3D`, zły rozkład wielkich liter),
- urwane linki kończące się na `@` lub na samym separatorze,
- listing istniejący tylko po polsku albo tylko po angielsku,
- powtórzone tagi.

Limity znaków platform to **wartości startowe** — siedzą w tabeli `platformy`
właśnie po to, żeby poprawić je przy pierwszym realnym eksporcie bez ruszania kodu.

## Zmiany względem oryginałów

Świadome odstępstwa, nie przypadki:

1. **Polskie znaki diakrytyczne.** Oryginały pisały „Polozenie”, „Panstwo”.
   Baza i widoki są w UTF-8, więc teksty mają pełną polszczyznę.
2. **Ziarno w generatorze sesji** — patrz wyżej.
3. **Pole „Rok / data” w typie „Postać”** było w oryginale widoczne, ale nigdy
   nie trafiało do wyniku. Teraz ląduje w Karcie postaci jako „Wzmiankowany”.
4. **Ukryte pola nie przeciekają.** Wartość pola niewidocznego dla danego typu
   jest odrzucana po stronie serwera, nie tylko chowana w UI.
