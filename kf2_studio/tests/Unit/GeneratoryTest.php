<?php

declare(strict_types=1);

namespace Tests\Unit;

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Domain\SessionGenerator;
use App\Domain\Template;
use App\Domain\WikiGenerator;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

/**
 * Rdzen generatorow nie zalezy od Laravela - te testy dzialaja bez bazy.
 * Ten sam zakres pokrywa tools/smoke.php, uruchamialny bez composera.
 */
final class GeneratoryTest extends TestCase
{
    private function wiki(): WikiGenerator
    {
        return new WikiGenerator(require __DIR__.'/../../database/data/wiki_types.php');
    }

    private function sesje(): SessionGenerator
    {
        return new SessionGenerator(require __DIR__.'/../../database/data/session_data.php');
    }

    public function test_szablon_oznacza_braki_jako_luki(): void
    {
        $this->assertSame('[UZUPEŁNIJ: wiek]', Template::render('{@wiek}', []));
        $this->assertSame('Marlua', Template::render('{nazwa|@imię}', ['nazwa' => 'Marlua']));
    }

    public function test_grupa_warunkowa_wybiera_galaz(): void
    {
        $szablon = '[[panstwo? w {panstwo}||w Fallathanie]]';

        $this->assertSame(' w Amarth', Template::render($szablon, ['panstwo' => 'Amarth']));
        $this->assertSame('w Fallathanie', Template::render($szablon, []));
    }

    public function test_kazdy_typ_artykulu_renderuje_sie_bez_surowych_tokenow(): void
    {
        foreach ($this->wiki()->typy() as $typ) {
            $wynik = $this->wiki()->generuj($typ['klucz'], ['nazwa' => 'Test']);

            $this->assertDoesNotMatchRegularExpression('/\{[a-z@]|\[\[/u', $wynik, "typ {$typ['klucz']}");
        }
    }

    public function test_ukryte_pola_nie_przeciekaja_do_artykulu(): void
    {
        // Typ "rasa" nie pokazuje pola panstwo, wiec nie moze go uzyc.
        $wynik = $this->wiki()->generuj('rasa', ['nazwa' => 'Ruani', 'panstwo' => 'Amarth']);

        $this->assertStringNotContainsString('Amarth', $wynik);
    }

    public function test_sesja_jest_odtwarzalna_z_ziarna(): void
    {
        $wejscie = ['motywy' => ['intryga'], 'miejsce' => 'Marlua', 'ton' => 'mroczny'];

        $this->assertSame(
            $this->sesje()->generuj($wejscie, 4242),
            $this->sesje()->generuj($wejscie, 4242),
        );
        $this->assertNotSame(
            $this->sesje()->generuj($wejscie, 4242),
            $this->sesje()->generuj($wejscie, 777),
        );
    }

    public function test_sesja_fg_wymusza_notke_o_wiesci(): void
    {
        $fg = $this->sesje()->generuj(['rodzaj' => 'fg', 'motywy' => ['bitwa']], 1);
        $prywatna = $this->sesje()->generuj(['rodzaj' => 'prywatna', 'motywy' => ['bitwa']], 1);

        $this->assertStringContainsString('podsumowania Wieścią', $fg);
        $this->assertStringNotContainsString('podsumowania Wieścią', $prywatna);
    }

    /** @return array<string, mixed> Poprawny wpis rejestru - punkt odniesienia. */
    private function wpis(array $nadpisania = []): array
    {
        return array_merge([
            'sku' => 'KF2-CASTLE-DOFLOT-001',
            'swiat' => 'kf2',
            'kolekcja' => 'Build The World You Play',
            'tytul_sprzedazowy' => 'KF2 Castle Doflot - Fantasy RPG Terrain - WorkShop3D',
            'nazwa_pl' => 'Zamek Doflot',
            'nazwa_en' => 'Castle Doflot',
            'opis_en' => 'A modular castle for tabletop RPG.',
            'opis_pl' => 'Modułowy zamek do gier bitewnych.',
            'tagi' => ['Fantasy RPG', 'castle'],
            'licencja_podstawowa' => 'Personal Use',
            'link_lore' => 'https://wiki.kf2.pl/Castle_Doflot',
        ], $nadpisania);
    }

    private function exporter(): ListingExporter
    {
        return new ListingExporter(require __DIR__.'/../../database/data/platforms.php');
    }

    public function test_zestaw_domyslny_ma_kolejnosc_z_sekcji_13(): void
    {
        $slugi = array_column($this->exporter()->platformyDomyslne(), 'slug');

        $this->assertSame(['cults3d', 'thangs', 'creality_eu', 'creality_cn'], $slugi);
    }

    public function test_eksport_normalizuje_tagi_pod_platforme(): void
    {
        $eksport = $this->exporter()->dlaPlatformy($this->wpis(), 'cults3d');

        $this->assertSame(['fantasy-rpg', 'castle'], $eksport['tagi']);
    }

    public function test_paczka_zawiera_pliki_katalogu_06(): void
    {
        $pliki = $this->exporter()->plikiPaczki($this->wpis());

        foreach (['TITLE.txt', 'DESCRIPTION_CULTS3D.txt', 'TAGS_CC_CN.txt'] as $nazwa) {
            $this->assertArrayHasKey($nazwa, $pliki);
        }
    }

    public function test_poprawny_wpis_nie_blokuje_wystawienia(): void
    {
        $linter = new ListingLinter();

        $this->assertFalse($linter->blokuje($linter->sprawdz($this->wpis())));
    }

    /**
     * @param array<string, mixed> $nadpisania
     */
    #[DataProvider('przypadkiBlokujace')]
    public function test_linter_blokuje_naruszenia_systemu(string $kod, array $nadpisania): void
    {
        $linter = new ListingLinter();
        $uwagi = $linter->sprawdz($this->wpis($nadpisania));

        $blokujace = array_column(
            array_filter($uwagi, static fn (array $u): bool => $u['waga'] === 'blokuje'),
            'kod',
        );

        $this->assertContains($kod, $blokujace);
    }

    /** @return array<string, array{0: string, 1: array<string, mixed>}> */
    public static function przypadkiBlokujace(): array
    {
        return [
            'literowka w marce' => ['marka', ['tytul_sprzedazowy' => 'KF2 Castle - Terrain - WorShop3D']],
            'urwany link' => ['link', ['opis_en' => 'Profil: https://przyklad.pl/@']],
            'KF2 poza KF2' => ['kf2_poza_kf2', ['swiat' => 'niezalezny', 'link_lore' => '']],
            'brak zrodla lore' => ['lore_bez_zrodla', ['link_lore' => '', 'zrodlo_lore' => '']],
            'niepotwierdzone supportless' => ['niepotwierdzona_deklaracja', ['opis_en' => 'Supportless print.']],
            'brak licencji' => ['brak_licencji', ['licencja_podstawowa' => '']],
            'PUBLISHED bez linku' => ['publikacja_bez_linku', ['status' => 'PUBLISHED']],
            'obca kolekcja' => ['kufel_i_kosci', ['kolekcja' => 'Castles', 'krotki_opis' => 'Kufel i Kości set.']],
        ];
    }

    public function test_nazwa_pliku_wg_sekcji_8(): void
    {
        $linter = new ListingLinter();

        $this->assertSame([], $linter->sprawdzNazwePliku('Castle_Doflot_print_ready_v1.stl'));
        $this->assertNotEmpty($linter->sprawdzNazwePliku('Zamek Doflot wieża.stl'));
        $this->assertNotEmpty($linter->sprawdzNazwePliku('Castle_final_final2.stl'));
    }
}
