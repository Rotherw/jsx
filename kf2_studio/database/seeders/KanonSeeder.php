<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\KanonFakt;
use App\Models\KanonWpis;
use Illuminate\Database\Seeder;

/**
 * Kanon KF2 z database/data/canon.php.
 * Seeder jest idempotentny - mozna go puscic ponownie po zmianie pliku danych.
 */
class KanonSeeder extends Seeder
{
    public function run(): void
    {
        $dane = require database_path('data/canon.php');

        foreach ($dane['facts'] as $i => $fakt) {
            KanonFakt::updateOrCreate(
                ['klucz' => $fakt['klucz']],
                ['etykieta' => $fakt['etykieta'], 'wartosc' => $fakt['wartosc'], 'kolejnosc' => $i],
            );
        }

        $kategorie = [
            'kontynent' => $dane['kontynenty'],
            'panstwo' => $dane['panstwa'],
            'ksiestwo' => $dane['ksiestwa_imperium'],
            'rasa' => $dane['rasy'],
            'frakcja' => array_merge($dane['rasy'], $dane['frakcje_dodatkowe']),
            'lokacja' => $dane['lokacje'],
            'charakter' => $dane['charaktery'],
        ];

        foreach ($kategorie as $kategoria => $wartosci) {
            foreach (array_values($wartosci) as $i => $wartosc) {
                KanonWpis::updateOrCreate(
                    ['kategoria' => $kategoria, 'wartosc' => $wartosc],
                    ['kolejnosc' => $i],
                );
            }
        }
    }
}
