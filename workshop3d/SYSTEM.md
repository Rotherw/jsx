# WorkShop3D × KF2 — System Operacyjny v2.0

**Stan dokumentu źródłowego:** 18.07.2026 · zastępuje „Nasz System v1"

Przeniesione do repozytorium z Google Drive (`Doku.Ws3d/WorkShop3D_KF2 _System_2.0.txt`,
18 330 B). Na Drive leżą jeszcze dwie **identyczne** kopie v1 w korzeniu
(`Zasada działania wdrożenia do ws3d` i `wdrożenie jak działa ws3d`, po 29 668 B)
— po weryfikacji tej wersji można je usunąć.

To jest dokument wiążący dla kodu w `kf2_studio/`. Gdy się rozejdzie z kodem,
rację ma dokument.

---

## 1. Cel

Rafał podejmuje decyzję, co tworzymy, i zatwierdza produkt. System przejmuje
mechanikę: porządkowanie plików, nazewnictwo, SKU i rejestr, opisy i tagi,
licencje, ustawienia ofert, pakowanie, przygotowanie publikacji, wspomagane
wystawianie, zapis linków i statusów.

## 2. Podział pracy

| Aktor | Odpowiada za |
|---|---|
| **Rafał** | temat i kolejność, przypisanie do KF2, generowanie/zatwierdzanie w MeshyAI, geometria i przygotowanie pod druk, potwierdzenie realnych parametrów wydruku, cena, licencja, publikacja, decyzje kreatywne |
| **ChatGPT / GPT** | obrazy referencyjne pod Image-to-3D, prompty do MeshyAI, analiza screenów i plików, nazwy PL/EN, SKU i wpis do rejestru, opisy, tagi, kategorie, propozycja ceny, okładki i rendery, pakiet sprzedażowy, kontrola spójności |
| **Claude w przeglądarce** | pobiera materiały z folderu synchronizowanego, uzupełnia formularze platform, dodaje pliki/grafiki/opis/tagi, publikuje **tylko po jednoznacznym poleceniu**, zwraca link albo dokładny błąd |
| **Segregator Commander V3** | skanuje lokalizacje, grupuje powiązane pliki, **kopiuje** je do paczki produktu, przygotowuje podglądy i `GOTOWE_DO_SKLEPU`; nie usuwa, nie nadpisuje, nie loguje się do platform, nie publikuje sam |

## 3. Tryb „pierwszy strzał"

Po otrzymaniu screena / folderu / plików — bez długiego wywiadu, od razu możliwie
pełny wynik.

Z jednego screena **można** przygotować: nazwę, bezpieczną klasyfikację, wstępny
opis, słowa kluczowe, prompt do MeshyAI, kierunek okładki.

Sam screen **nie potwierdza**: wymiarów, skali, liczby plików, testu wydruku,
wymagania podpór, zawartości 3MF, rodzaju licencji.

- brak blokuje publikację → jedno krótkie pytanie,
- brak nie blokuje przygotowania → `DO UZUPEŁNIENIA` i lecimy dalej.

## 4. Pipeline produktu

| Faza | Zakres |
|---|---|
| 0 | Decyzja: co, do jakiej serii, pojedynczy/zestaw/lejek, gdzie wystawiamy |
| 1 | Obraz referencyjny: PNG 1024×1024, jeden obiekt centralnie, izometria 3/4, neutralny clay, bez tła/napisów/logo, bez elementów w powietrzu, geometria wykonalna na FDM |
| 2 | Generowanie 3D w MeshyAI, wybór wariantu, pobranie plików, zapis źródłowego PNG + GLB/STL |
| 3 | Przygotowanie do druku: naprawa siatki, płaskie dno, cienkie elementy, podział jeśli naprawdę potrzebny, skala, STL/3MF, próbny wydruk lub kontrola orientacji |
| 4 | Prezentacja: `COVER.png`, `THANGS_COVER.png`, `PRODUCT_RENDER_01/02.png`, render 45° z góry, opcjonalne zdjęcie wydruku i film |
| 5 | Paczka i rejestr: uporządkowanie plików, nazwy, `meta.json`, wpis do rejestru, dokumentacja i licencja |
| 6 | Listing: tytuły, opisy, tagi, kategorie, cena, instrukcja druku, ustawienia platform, CTA |
| 7 | Publikacja: Thangs, Cults3D, Creality Cloud EU, Creality Cloud CN |
| 8 | Zamknięcie wydania: link, data, cena, licencja, status, post, powiązania z KF2 / Muza RPG |

Nie deklarujemy „supportless", „print tested" ani konkretnych ustawień, jeśli nie
zostały sprawdzone. Render nie może być nazywany zdjęciem wydruku.

## 5. Source of truth

> **Zmiana względem dokumentu z 18.07:** workflow przeniesiony na Google Drive.
> Gotowe modele do publikacji zaczynają się od folderu `Folder Sync` na Drive,
> a nie od lokalnego drzewa na `C:`.

```
Google Drive  Folder Sync/Gotowe do sklepu   ← wejście: gotowe do publikacji
Google Drive  Folder Sync/Opublikowane       ← po pełnym przebiegu
Nextcloud     Folder Sync                    ← magazyn posprzedażowy (jednostronnie)
```

Drive `Folder Sync` (id `1bKkH3_P2XYCtFtSv4HlzmWE16cqjYGlo`) jest obszarem
roboczym i źródłem prawdy. Nextcloud `Folder Sync` na `cloud.workshop3d.pl` to
archiwum: pliki lecą **tylko w jedną stronę**, Drive → Nextcloud.

Historyczne lokalizacje lokalne (nadal magazyn źródeł Segregatora):

```
C:\Users\RafałKarwowski\WorkShop3D\WorkShop3D\Segregator\MAGAZYN
GOTOWE_DO_SKLEPU
```

- jeden produkt = jeden główny folder,
- oryginały nigdy nie są usuwane ani nadpisywane,
- Segregator kopiuje pliki, nie przenosi ich,
- folder produktu jest źródłem prawdy,
- folder synchronizacji platformy to tylko kopia wydania,
- ZIP jest eksportem, nie źródłem prawdy — powstaje na żądanie,
- nie umieszczamy obok siebie folderu i identycznego ZIP-a w Thangs Sync,
- ścieżka istniejąca wyłącznie na Nextcloud zostaje nietknięta — to archiwum
  trzyma paczkę już sprzątniętą z obszaru roboczego,
- gdy ten sam plik różni się po obu stronach, wygrywa kopia z Drive'a, nawet
  jeśli wersja w archiwum jest nowsza.

Realizacja: `workshop3d_publisher`, `cloud_sync.mirror_direction`
(domyślnie `google_to_nextcloud`).

## 6. Struktura paczki Commander V3

```
Product_Name/
  00_GOTOWE_DO_SKLEPU.txt
  meta.json
  01_SOURCE/            source_image.png · original_files · project_sources
  02_STL/               Product_Name_print_ready_v1.stl
  03_3MF/               Product_Name_profile_v1.3mf
  04_GLB_UI_GAME/       Product_Name_preview_v1.glb
  05_PNG_RENDERS/       COVER.png · THANGS_COVER.png · PRODUCT_RENDER_01.png
                        PRODUCT_RENDER_02.png · PRINT_PHOTO_OPTIONAL.png
  06_THANGS_LISTING/    TITLE.txt · SHORT_DESCRIPTION.txt
                        DESCRIPTION_THANGS.txt   · TAGS_THANGS.txt
                        DESCRIPTION_CULTS3D.txt  · TAGS_CULTS3D.txt
                        DESCRIPTION_CC_EU.txt    · TAGS_CC_EU.txt
                        DESCRIPTION_CC_CN.txt    · TAGS_CC_CN.txt
                        CHANGELOG_OPTIONAL.txt
  07_PRINT_SETTINGS/    PRINT_SETTINGS_FDM.txt · PRINT_SETTINGS_RESIN_OPTIONAL.txt
                        ORIENTATION_NOTES.txt  · ASSEMBLY_NOTES_OPTIONAL.txt
  08_LICENSE_README/    README_PL.txt · README_EN.txt · LICENSE.txt
                        COMMERCIAL_LICENSE_NOTES.txt
  09_VIDEO_OPTIONAL/    trailer · short · timelapse
  10_ZIP_EXPORT/        Product_Name_v1.zip
```

Numeracji nie zmieniamy, dopóki Commander V3 nie zostanie świadomie zaktualizowany.

> Moduł Listingi w `kf2_studio/` generuje zawartość katalogu `06_THANGS_LISTING`
> — patrz `ListingExporter::plikiPaczki()`.

## 7. Rejestr modelu

**Tożsamość** — SKU, nazwa PL, nazwa EN, tytuł sprzedażowy, slug/folder, typ
produktu, kolekcja, wersja.

**Świat** — KF2 / niezależny / inny projekt, lokacja, frakcja, postać, źródło
lore, bezpośredni link do wiki lub materiału właściciela.

**Produkcja** — dostępne formaty, liczba elementów, skala lub wymiary,
technologia, ustawienia druku, stan testu, wymaganie podpór, data przygotowania.

**Sprzedaż** — cena, wersja darmowa/płatna, licencja podstawowa, ewentualna
komercyjna, limit sprzedaży wydruków, zawartość zestawu.

**Dystrybucja** — platforma, status, data publikacji, link, wersja plików,
cover, film, powiązany post, powiązanie z Muza RPG i KF2.

**Statusy:** `SOURCE` · `IN_PROGRESS` · `READY_TO_UPLOAD` · `UPLOADED` ·
`PUBLISHED` · `NEEDS_UPDATE` · `ARCHIVED`

**SKU po nadaniu nie zmienia się i nie może zostać użyte ponownie.**

## 8. Nazewnictwo

Marka zawsze: **`WorkShop3D`**

Tytuł KF2: `KF2 [Model Name] - [Search Descriptor] - WorkShop3D`

```
KF2 House Anthal - Medieval Fantasy RPG Terrain - WorkShop3D
KF2 Tower Nordenheim - Fantasy RPG Terrain - WorkShop3D
```

Pliki: angielski, ASCII, bez polskich znaków, podkreślniki zamiast spacji,
wersjonowanie `v1` / `v1_1` / `repaired` / `print_ready` / `source`, bez nazw
typu `final_final2`. Bez słowa „Chibi" w tytule sprzedażowym, chyba że Rafał
wyraźnie tego chce. Prefiks `KF2` tylko dla produktów KF2. „Kufel i Kości"
tylko dla prawdziwych elementów tej kolekcji.

## 9. Komplet metadanych

Nazwa kanoniczna PL · nazwa kanoniczna EN · główny tytuł sprzedażowy · skrócony
tytuł platformowy · SKU · typ i kolekcja · krótki opis · opis EN · opis PL (jeśli
potrzebny) · opis zlokalizowany dla CC CN · rzeczywista lista plików ·
potwierdzone ustawienia druku · licencja · tagi osobno dla każdej platformy ·
kategoria · rekomendacja ceny · ustawienia formularza platformy · tytuł posta
i CTA · lore ze źródłem · status i link po publikacji.

Cena bazowa: pojedynczy model ~4,99 USD; zestaw trzech ~12,99–14,99 USD —
zawsze korygowana według realnej zawartości i złożoności.

## 10. Żelazne reguły faktów i lore

1. Zero zmyślania.
2. Lore KF2 wyłącznie z: wiki.kf2.pl, materiału przekazanego przez Rafała, innego
   potwierdzonego źródła właściciela świata.
3. Do wpisu zawsze dołączamy link albo informację o źródle.
4. Brak dostępu = `BRAK DOSTĘPU — PODAJ LINK LUB WKLEJ TREŚĆ`.
5. Screen nie potwierdza parametrów technicznych.
6. Nie wymyślamy skali, wymiarów, liczby części, testu druku, braku podpór,
   zawartości 3MF, licencji ani właściciela praw.
7. Okładka nie może pokazywać elementów, których nie ma w zestawie.
8. Nie oznaczamy modelu jako AI-generated bez sprawdzenia, czego dotyczy pole
   platformy i bez potwierdzenia pochodzenia.
9. Wolno uczciwie użyć określenia „AI-assisted workflow", jeśli odpowiada procesowi.

## 11. Licencje

Jedna podstawowa licencja obowiązująca we wszystkich miejscach publikacji. Nie
może być tak, że ten sam produkt na jednej platformie pozwala sprzedawać wydruki,
na innej tego zabrania, a opis nie wyjaśnia różnicy.

Poziomy: **Personal Use** · **Commercial/Merchant** · **Subscription Merchant Licence**

- zakaz redystrybucji plików cyfrowych,
- brak prawa do odsprzedaży lub udostępniania STL/3MF/GLB,
- sprzedaż fizycznych wydruków tylko przy potwierdzonej licencji komercyjnej,
- dokładny limit sprzedaży wpisujemy wprost,
- praw komercyjnych z jednego planu nie przenosimy automatycznie na inną platformę,
- prawa do świata KF2 i nazw własnych przypisujemy zgodnie z rzeczywistym właścicielem,
- nie przypisujemy WorkShop3D cudzej własności intelektualnej.

## 12. Standard grafik

Obraz pod MeshyAI i okładka sprzedażowa to **dwa różne materiały**.

**Obraz pod MeshyAI:** jeden obiekt, 1024×1024, bez tła, napisów, marki
i dekoracji, widok 3/4, neutralny clay, czytelna konstrukcja.

**Okładka produktowa:** wiernie pokazuje sprzedawany model, nie zmienia
geometrii, nie udaje dodatkowej zawartości, zawiera markę WorkShop3D, dla KF2
może zawierać KRONIKI FALLATHANU w stylu Uncial Antiqua, pokazuje formaty tylko
wtedy, gdy naprawdę są w paczce.

Hierarchia okładki KF2: **KRONIKI FALLATHANU** → nazwa modelu/kolekcji → **WorkShop3D**

## 13. Priorytet platform

Domyślnie: **1. Cults3D · 2. Thangs · 3. Creality Cloud EU · 4. Creality Cloud CN**

Tylko na osobne polecenie: MyMiniFactory, Printables, MakerWorld, 3DExport, Threeding.

- formularz i limity **zawsze** sprawdzamy podczas wystawiania,
- nie opieramy się ślepo na starych limitach tagów,
- Thangs Sync: jeden folder najwyższego poziomu = jeden produkt,
- nie dodajemy folderu oraz identycznego ZIP-a jako dwóch modeli,
- płatny STL/ZIP nie może przypadkowo zostać wystawiony jako publiczny darmowy plik,
- Creality Cloud EU i CN otrzymują osobne, dopasowane listingi,
- publikację uznajemy za wykonaną dopiero po otrzymaniu **działającego linku**.

Nie kierujemy ruchu na workshop3d.pl, dopóki strona nie zostanie oczyszczona
z szablonu NFT/ETH.

## 14. Kontrola przed publikacją

```
[ ] Czy jeden folder oznacza jeden produkt?
[ ] Czy tytuł, folder i główny plik mają spójną nazwę?
[ ] Czy SKU zgadza się z rejestrem?
[ ] Czy lista plików odpowiada rzeczywistej zawartości?
[ ] Czy STL/3MF/GLB dają się otworzyć?
[ ] Czy cover pokazuje tylko zawartość zestawu?
[ ] Czy render nie jest opisany jako zdjęcie wydruku?
[ ] Czy parametry druku zostały potwierdzone?
[ ] Czy skala i wymiary są prawdziwe?
[ ] Czy licencja jest spójna?
[ ] Czy tagi pasują do typu produktu?
[ ] Czy NPC nie otrzymał automatycznie tagów terrain?
[ ] Czy branding KF2 użyto tylko dla KF2?
[ ] Czy „Kufel i Kości" jest właściwą kolekcją?
[ ] Czy płatne pliki nie są publicznie dostępne?
[ ] Czy nie istnieje duplikat folder + ZIP?
[ ] Czy ZIP zawiera README i LICENSE?
[ ] Czy oferta ma działający link?
[ ] Czy link został zapisany w rejestrze?
```

Pozycje sprawdzalne maszynowo realizuje `ListingLinter` w `kf2_studio/`.

## 15. System sprzedażowy

Podstawowa ścieżka: darmowy model lub element → płatny zestaw → profil
i kolekcja → subskrypcja → licencja komercyjna.

Równoległe lejki: darmowy Harold → kolekcja „Kufel i Kości"; darmowa beczka
i skrzynia → Tavern Props Pack; model z filmu → pełna kolekcja; Muza RPG →
model związany z lore KF2.

Każde wydanie dostaje: CTA do właściwego produktu, link do kolekcji, link do
profilu, materiał na YouTube/TikTok/Instagram/FB, powiązanie z KF2 lub Muza RPG
— jeśli jest prawdziwe.

## 16. Reality check

Nie istnieje bezpieczny, uniwersalny przycisk publikujący model na wszystkich
platformach. Realny system to: jedno źródło prawdy, jedna paczka produktu,
automatyczne metadane, osobne teksty platformowe, wspomagane uzupełnianie
formularzy, publikacja po zatwierdzeniu, zapis linków i statusów.

Cel: z kilku godzin przeklejania zejść do kilku–kilkunastu minut kontroli
i zatwierdzania.

## 17. Ekosystem

Creality Cloud (najmocniejszy) · Thangs · Cults3D · MyMiniFactory · Printables ·
YouTube · Instagram · TikTok · FB „Druk 3D Mrągowo" · **Muza RPG** (Suno,
licencja komercyjna — lead-magnety) · KF2 / rpg.city / wiki.kf2.pl
