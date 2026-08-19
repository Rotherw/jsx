<?php

declare(strict_types=1);

/**
 * Test dymny rdzenia generatorow - dziala na golym PHP, bez composera.
 * Uruchomienie:  php tools/smoke.php
 */

$baza = dirname(__DIR__);
spl_autoload_register(static function (string $klasa) use ($baza): void {
    if (! str_starts_with($klasa, 'App\\')) {
        return;
    }
    $sciezka = $baza.'/app/'.str_replace('\\', '/', substr($klasa, 4)).'.php';
    if (is_file($sciezka)) {
        require $sciezka;
    }
});

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Domain\SessionGenerator;
use App\Domain\Template;
use App\Domain\WikiGenerator;

$bledy = 0;
$testy = 0;

function sprawdz(string $opis, bool $warunek, string $szczegoly = ''): void
{
    global $bledy, $testy;
    $testy++;
    if ($warunek) {
        echo "  ok   {$opis}\n";

        return;
    }
    $bledy++;
    echo "  FAIL {$opis}\n";
    if ($szczegoly !== '') {
        echo "       {$szczegoly}\n";
    }
}

echo "\n== Template ==\n";
sprawdz('pole podstawiane', Template::render('{nazwa}', ['nazwa' => 'Marlua']) === 'Marlua');
sprawdz('tekst zapasowy', Template::render('{nazwa|Bezimienne}', []) === 'Bezimienne');
sprawdz('luka z {@}', Template::render('{@wiek}', []) === '[UZUPEŁNIJ: wiek]');
sprawdz('luka przez {pole|@}', Template::render('{nazwa|@imię}', []) === '[UZUPEŁNIJ: imię]');
sprawdz('grupa spelniona', Template::render('[[panstwo? w {panstwo}||nigdzie]]', ['panstwo' => 'Amarth']) === ' w Amarth');
sprawdz('grupa niespelniona', Template::render('[[panstwo? w {panstwo}||nigdzie]]', []) === 'nigdzie');
sprawdz('grupa bez galezi else', Template::render('X[[rok? ({rok})]]', []) === 'X');
sprawdz('pole wewnatrz luki', Template::render('[[panstwo?{@gdzie (np. {panstwo})}]]', ['panstwo' => 'Ostwald']) === '[UZUPEŁNIJ: gdzie (np. Ostwald)]');
sprawdz('klamry z danych nie psuja szablonu', ! str_contains(Template::render('{nazwa} {@x}', ['nazwa' => 'a{b}c']), '{b}'));

echo "\n== WikiGenerator ==\n";
$wiki = new WikiGenerator(require $baza.'/database/data/wiki_types.php');
sprawdz('9 typow artykulow', count($wiki->typy()) === 9, 'jest '.count($wiki->typy()));

$art = $wiki->generuj('lokacja', [
    'nazwa' => 'Równina Płomieni',
    'panstwo' => 'Amarth',
    'zarys' => 'Solidna budowla z czarnej, magmowej skały.',
], 'klimatyczny');
sprawdz('naglowek wiki', str_starts_with($art, '= Równina Płomieni ='));
sprawdz('lead klimatyczny uzyty', str_contains($art, 'na długo zostaje w pamięci'));
sprawdz('panstwo w Polozeniu', str_contains($art, 'Położenie: Amarth.'));
sprawdz('zarys trafil do Opisu', str_contains($art, 'Solidna budowla'));
sprawdz('luki oznaczone', Template::maLuki($art));
sprawdz('brak surowych tokenow', ! preg_match('/\{[a-z@]/u', $art), $art);
sprawdz('brak niezamknietych grup', ! str_contains($art, '[['));

$plain = $wiki->generuj('lokacja', ['nazwa' => 'Marlua'], 'domyslny', WikiGenerator::FORMAT_TEKST, true);
sprawdz('format tekstowy - wersaliki', str_starts_with($plain, 'RÓWNINA') === false && str_starts_with($plain, 'MARLUA'));
sprawdz('format tekstowy - naglowki z dwukropkiem', str_contains($plain, '1. Położenie:'));
sprawdz('stopka dodana', str_contains($plain, WikiGenerator::STOPKA));
sprawdz('lokacja bez panstwa -> Fallathan', str_contains($plain, 'lokacja w Fallathanie'));

$postac = $wiki->generuj('postac', [
    'nazwa' => 'Stary Kowal', 'rasa' => 'Krasnoludy', 'rola' => 'kowal',
    'panstwo' => 'Amarth', 'charakter' => 'Neutralny', 'rok' => '3340 NE',
]);
sprawdz('karta postaci: rasa', str_contains($postac, 'Rasa: Krasnoludy'));
sprawdz('karta postaci: pochodzenie', str_contains($postac, 'Pochodzenie: Amarth'));
sprawdz('karta postaci: rok wykorzystany', str_contains($postac, 'Wzmiankowany: 3340 NE'));

$rasa = $wiki->generuj('rasa', ['nazwa' => 'Ruani', 'panstwo' => 'Amarth']);
sprawdz('ukryte pole nie przecieka do tresci', ! str_contains($rasa, 'Amarth'), $rasa);

foreach ($wiki->typy() as $typ) {
    $wynik = $wiki->generuj($typ['klucz'], ['nazwa' => 'Test']);
    sprawdz("typ {$typ['klucz']} renderuje sie czysto", ! preg_match('/\{[a-z@]|\[\[/u', $wynik), $wynik);
}

echo "\n== SessionGenerator ==\n";
$sesje = new SessionGenerator(require $baza.'/database/data/session_data.php');
$wejscie = [
    'rodzaj' => 'fg', 'skala' => 'druzyna', 'dlugosc' => 'multi',
    'motywy' => ['intryga', 'sledztwo'], 'panstwo' => 'Imperium Vanthijskie',
    'miejsce' => 'Marlua', 'frakcja' => 'Elfy', 'ton' => 'polityczny',
];
$a = $sesje->generuj($wejscie, 12345);
$b = $sesje->generuj($wejscie, 12345);
$c = $sesje->generuj($wejscie, 999);
sprawdz('to samo ziarno -> ten sam wynik', $a === $b);
sprawdz('inne ziarno -> inny wynik', $a !== $c);
sprawdz('naglowek i sekcje', str_contains($a, '== Premisa ==') && str_contains($a, '== Sceny =='));
sprawdz('oba motywy w naglowku', str_contains($a, 'Intryga + Śledztwo'));
sprawdz('stawka z tonu', str_contains($a, 'układ sił, wpływy i przyszłe sojusze'));
sprawdz('miejsce wplecione w zaczepke', str_contains($a, 'Marlua'));
sprawdz('FG wymusza notke o Wiesci', str_contains($a, 'podsumowania Wieścią'));
sprawdz('frakcja w NPC', str_contains($a, 'Rasa: Elfy'));
sprawdz('3 zakonczenia', str_contains($a, "\n3. "));
sprawdz('wskazowki MG', str_contains($a, '== Wskazówki dla prowadzącego =='));
sprawdz('brak surowych tokenow', ! preg_match('/\{[a-z@]|\[\[/u', $a), $a);

$prywatna = $sesje->generuj(['rodzaj' => 'prywatna', 'motywy' => ['groza']], 7, false);
sprawdz('prywatna bez notki o Wiesci', ! str_contains($prywatna, 'podsumowania Wieścią'));
sprawdz('wskazowki MG wylaczalne', ! str_contains($prywatna, 'Wskazówki dla prowadzącego'));
sprawdz('brak miejsca -> Fallathan', str_contains($prywatna, 'Fallathan'));

$bezMotywu = $sesje->generuj(['motywy' => []], 42);
sprawdz('pusty motyw -> losowany', str_contains($bezMotywu, 'Motyw: '));

echo "\n== Listingi: eksport ==\n";
$platformy = require $baza.'/database/data/platforms.php';
$exporter = new ListingExporter($platformy);

$produkt = [
    'sku' => 'KF2-CASTLE-DOFLOT-001',
    'swiat' => 'kf2',
    'kolekcja' => 'Build The World You Play',
    'tytul_sprzedazowy' => 'KF2 Castle Doflot - Fantasy RPG Terrain - WorkShop3D',
    'nazwa_pl' => 'Zamek Doflot',
    'nazwa_en' => 'Castle Doflot',
    'krotki_opis' => 'Modular castle for tabletop RPG.',
    'opis_en' => "A **modular** castle for tabletop RPG.\n\nMore: https://workshop3d.example/models",
    'opis_pl' => 'Modułowy zamek do gier bitewnych.',
    'tagi' => ['Fantasy RPG', 'castle', 'tabletop terrain', 'KF2'],
    'licencja_podstawowa' => 'Personal Use',
    'link_lore' => 'https://wiki.kf2.pl/Castle_Doflot',
];

$domyslne = $exporter->platformyDomyslne();
sprawdz('zestaw domyslny to 4 platformy', count($domyslne) === 4, (string) count($domyslne));
sprawdz('kolejnosc wg sekcji 13',
    array_column($domyslne, 'slug') === ['cults3d', 'thangs', 'creality_eu', 'creality_cn'],
    implode(',', array_column($domyslne, 'slug')));

$cults = $exporter->dlaPlatformy($produkt, 'cults3d');
sprawdz('tagi lowercase z mysrednikami', $cults['tagi'] === ['fantasy-rpg', 'castle', 'tabletop-terrain', 'kf2'],
    implode(',', $cults['tagi']));
sprawdz('markdown usuniety gdy nieobslugiwany', ! str_contains($cults['opis'], '**'), $cults['opis']);
sprawdz('ostrzezenie o niepotwierdzonych limitach',
    (bool) array_filter($cults['ostrzezenia'], fn ($o) => str_contains($o, 'nie są potwierdzone')));

$cn = $exporter->dlaPlatformy($produkt, 'creality_cn');
sprawdz('CN bez linkow zewnetrznych', ! str_contains($cn['opis'], 'https://'), $cn['opis']);
sprawdz('CN sygnalizuje brak wlasnego opisu',
    (bool) array_filter($cn['ostrzezenia'], fn ($o) => str_contains($o, 'Creality Cloud CN')));

$dlugiTytul = $produkt;
$dlugiTytul['tytul_sprzedazowy'] = 'KF2 '.str_repeat('Bardzo Dlugi Tytul ', 6).'- Terrain - WorkShop3D';
$dlugiTytul['tytul_krotki'] = 'KF2 Doflot - Terrain - WorkShop3D';
$przyciety = $exporter->dlaPlatformy($dlugiTytul, 'creality_eu');
sprawdz('uzyto skroconego tytulu zamiast ciac', $przyciety['tytul'] === 'KF2 Doflot - Terrain - WorkShop3D',
    $przyciety['tytul']);

$pliki = $exporter->plikiPaczki($produkt);
foreach (['TITLE.txt', 'SHORT_DESCRIPTION.txt', 'DESCRIPTION_CULTS3D.txt', 'TAGS_CULTS3D.txt',
          'DESCRIPTION_THANGS.txt', 'TAGS_THANGS.txt', 'DESCRIPTION_CC_EU.txt', 'TAGS_CC_EU.txt',
          'DESCRIPTION_CC_CN.txt', 'TAGS_CC_CN.txt'] as $nazwaPliku) {
    sprawdz("paczka zawiera {$nazwaPliku}", array_key_exists($nazwaPliku, $pliki));
}
sprawdz('TITLE.txt to tytul sprzedazowy', $pliki['TITLE.txt'] === $produkt['tytul_sprzedazowy']);

echo "\n== Listingi: kontrola przed publikacja ==\n";
$linter = new ListingLinter();

$kody = fn (array $u): array => array_column($u, 'kod');
$blokujace = fn (array $u): array => array_column(array_filter($u, fn ($x) => $x['waga'] === 'blokuje'), 'kod');

sprawdz('czysty wpis nie blokuje', ! $linter->blokuje($linter->sprawdz($produkt)),
    implode(',', $blokujace($linter->sprawdz($produkt))));

$zLiterowka = array_merge($produkt, ['tytul_sprzedazowy' => 'KF2 Castle - Terrain - WorShop3D']);
sprawdz('literowka w marce blokuje', in_array('marka', $blokujace($linter->sprawdz($zLiterowka)), true));

$zUrwanym = array_merge($produkt, ['opis_en' => 'Profil: https://przyklad.pl/@']);
sprawdz('urwany link blokuje', in_array('link', $blokujace($linter->sprawdz($zUrwanym)), true));

$zlyWzorzec = array_merge($produkt, ['tytul_sprzedazowy' => 'Castle Doflot WorkShop3D']);
sprawdz('tytul poza wzorcem KF2 to uwaga', in_array('tytul_wzorzec', $kody($linter->sprawdz($zlyWzorzec)), true));

$niekf2 = array_merge($produkt, ['swiat' => 'niezalezny', 'link_lore' => '']);
sprawdz('prefiks KF2 poza KF2 blokuje', in_array('kf2_poza_kf2', $blokujace($linter->sprawdz($niekf2)), true));

$bezLore = array_merge($produkt, ['link_lore' => '', 'zrodlo_lore' => '']);
sprawdz('KF2 bez zrodla lore blokuje', in_array('lore_bez_zrodla', $blokujace($linter->sprawdz($bezLore)), true));

$deklaracja = array_merge($produkt, ['opis_en' => 'Supportless print, ready to go.']);
sprawdz('niepotwierdzone "supportless" blokuje',
    in_array('niepotwierdzona_deklaracja', $blokujace($linter->sprawdz($deklaracja)), true));
$potwierdzona = array_merge($deklaracja, ['wymaga_podpor' => false]);
sprawdz('potwierdzone "supportless" przechodzi',
    ! in_array('niepotwierdzona_deklaracja', $blokujace($linter->sprawdz($potwierdzona)), true));

$bezLicencji = array_merge($produkt, ['licencja_podstawowa' => '']);
sprawdz('brak licencji podstawowej blokuje', in_array('brak_licencji', $blokujace($linter->sprawdz($bezLicencji)), true));

$opublikowany = array_merge($produkt, ['status' => 'PUBLISHED']);
sprawdz('PUBLISHED bez linku blokuje',
    in_array('publikacja_bez_linku', $blokujace($linter->sprawdz($opublikowany)), true));
sprawdz('PUBLISHED z linkiem przechodzi',
    ! in_array('publikacja_bez_linku', $blokujace($linter->sprawdz(
        array_merge($opublikowany, ['link' => 'https://cults3d.com/x'])
    )), true));

$obcaKolekcja = array_merge($produkt, ['kolekcja' => 'Castles', 'krotki_opis' => 'Part of Kufel i Kości.']);
sprawdz('"Kufel i Kosci" poza kolekcja blokuje',
    in_array('kufel_i_kosci', $blokujace($linter->sprawdz($obcaKolekcja)), true));

$duplikat = array_merge($produkt, ['tagi' => ['a', 'A', 'b']]);
sprawdz('duplikat tagu to uwaga', in_array('tagi_duplikat', $kody($linter->sprawdz($duplikat)), true));

sprawdz('nazwa pliku ze spacja i polskim znakiem odrzucona',
    count($linter->sprawdzNazwePliku('Zamek Doflot wieża.stl')) >= 2);
sprawdz('poprawna nazwa pliku przechodzi',
    $linter->sprawdzNazwePliku('Castle_Doflot_print_ready_v1.stl') === []);
sprawdz('final_final2 odrzucone',
    $linter->sprawdzNazwePliku('Castle_final_final2.stl') !== []);

echo "\n----\n";
echo $bledy === 0 ? "OK: {$testy} testow przeszlo\n\n" : "BLEDY: {$bledy} z {$testy}\n\n";
exit($bledy === 0 ? 0 : 1);
