<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\SesjaMotyw;
use App\Models\SesjaSlownik;
use App\Models\SesjaTekst;
use Illuminate\Database\Seeder;

class SesjeSlownikiSeeder extends Seeder
{
    public function run(): void
    {
        $dane = require database_path('data/session_data.php');

        foreach ($dane['motywy'] as $i => $motyw) {
            SesjaMotyw::updateOrCreate(
                ['klucz' => $motyw['klucz']],
                [
                    'etykieta' => $motyw['etykieta'],
                    'tytuly' => $motyw['tytuly'],
                    'zaczepki' => $motyw['zaczepki'],
                    'kolejnosc' => $i,
                ],
            );
        }

        $slowniki = [
            'ton' => $dane['tony'],
            'rodzaj' => $dane['rodzaje'],
            'skala' => $dane['skale'],
            'dlugosc' => $dane['dlugosci'],
        ];

        foreach ($slowniki as $rodzaj => $wpisy) {
            foreach ($wpisy as $i => $wpis) {
                $atrybuty = $wpis;
                unset($atrybuty['klucz'], $atrybuty['etykieta']);

                SesjaSlownik::updateOrCreate(
                    ['rodzaj' => $rodzaj, 'klucz' => $wpis['klucz']],
                    ['etykieta' => $wpis['etykieta'], 'atrybuty' => $atrybuty, 'kolejnosc' => $i],
                );
            }
        }

        $teksty = [
            'komplikacja' => $dane['komplikacje'],
            'kulminacja' => $dane['kulminacje'],
            'zakonczenie' => $dane['zakonczenia'],
            'wskazowka_mg' => $dane['wskazowki_mg'],
        ];

        foreach ($teksty as $rodzaj => $lista) {
            SesjaTekst::where('rodzaj', $rodzaj)->delete();
            foreach ($lista as $i => $tresc) {
                SesjaTekst::create(['rodzaj' => $rodzaj, 'tresc' => $tresc, 'kolejnosc' => $i]);
            }
        }
    }
}
