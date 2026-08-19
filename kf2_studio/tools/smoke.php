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

echo "\n== Listingi ==\n";
$platformy = require $baza.'/database/data/platforms.php';
$exporter = new ListingExporter($platformy);
$produkt = [
    'tytul_en' => 'Castle Doflot KF2 - Fantasy RPG Terrain - WorkShop3D',
    'tytul_pl' => 'Zamek Doflot KF2 - teren do RPG - WorkShop3D',
    'opis_en' => "A modular castle for tabletop RPG.\n\nMore: https://workshop3d.example/@rotherw28",
    'opis_pl' => 'Modułowy zamek do gier bitewnych.',
    'tagi' => ['Fantasy RPG', 'castle', 'tabletop terrain', 'KF2'],
];
$eksport = $exporter->dlaPlatformy($produkt, 'printables');
sprawdz('tagi bez spacji na Printables', $eksport['tagi'] === ['fantasy-rpg', 'castle', 'tabletop-terrain', 'kf2'], implode(',', $eksport['tagi']));
sprawdz('tytul przyciety do limitu', mb_strlen($eksport['tytul']) <= 60);
$cn = $exporter->dlaPlatformy($produkt, 'creality_cn');
sprawdz('CN bez linkow zewnetrznych', ! str_contains($cn['opis'], 'https://'), $cn['opis']);
sprawdz('limit tagow Cults3D', count($exporter->dlaPlatformy($produkt, 'cults3d')['tagi']) <= 10);

$linter = new ListingLinter();
$uwagi = $linter->sprawdz([
    'tytul_en' => 'Castle Doflot KF2 - WorShop3D',
    'tytul_pl' => 'Zamek Doflot KF2 - WorkShop3D',
    'opis_en' => 'Zobacz @ https://przyklad.pl/@',
    'opis_pl' => '',
    'tagi' => ['a', 'a', 'b'],
]);
$kody = array_column($uwagi, 'kod');
sprawdz('wykrywa literowke w marce', in_array('marka', $kody, true), implode(',', $kody));
sprawdz('wykrywa urwany link z @', in_array('link', $kody, true), implode(',', $kody));
sprawdz('wykrywa duplikat tagu', in_array('tagi_duplikat', $kody, true), implode(',', $kody));
sprawdz('wykrywa brak opisu PL', in_array('brak_tlumaczenia', $kody, true), implode(',', $kody));
sprawdz('czysty listing bez uwag', $linter->sprawdz([
    'tytul_en' => 'Castle Doflot KF2 - Fantasy RPG Terrain - WorkShop3D',
    'tytul_pl' => 'Zamek Doflot KF2 - teren RPG - WorkShop3D',
    'opis_en' => 'A modular castle.', 'opis_pl' => 'Modułowy zamek.',
    'tagi' => ['castle', 'rpg'],
]) === []);

echo "\n----\n";
echo $bledy === 0 ? "OK: {$testy} testow przeszlo\n\n" : "BLEDY: {$bledy} z {$testy}\n\n";
exit($bledy === 0 ? 0 : 1);
