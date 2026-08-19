<?php

declare(strict_types=1);

namespace Tests\Unit;

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Domain\SessionGenerator;
use App\Domain\Template;
use App\Domain\WikiGenerator;
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

    public function test_eksport_normalizuje_tagi_i_limity(): void
    {
        $exporter = new ListingExporter(require __DIR__.'/../../database/data/platforms.php');

        $eksport = $exporter->dlaPlatformy([
            'tytul_en' => 'Castle', 'opis_en' => 'Opis', 'tagi' => ['Fantasy RPG', 'Castle'],
        ], 'printables');

        $this->assertSame(['fantasy-rpg', 'castle'], $eksport['tagi']);
    }

    public function test_linter_lapie_literowke_w_marce_i_urwany_link(): void
    {
        $uwagi = (new ListingLinter())->sprawdz([
            'tytul_en' => 'Castle - WorShop3D',
            'tytul_pl' => 'Zamek - WorkShop3D',
            'opis_en' => 'https://przyklad.pl/@',
            'opis_pl' => 'Opis',
            'tagi' => [],
        ]);

        $kody = array_column($uwagi, 'kod');
        $this->assertContains('marka', $kody);
        $this->assertContains('link', $kody);
    }
}
