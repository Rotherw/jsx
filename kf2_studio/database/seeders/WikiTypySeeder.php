<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\WikiTyp;
use Illuminate\Database\Seeder;

class WikiTypySeeder extends Seeder
{
    public function run(): void
    {
        foreach (require database_path('data/wiki_types.php') as $i => $typ) {
            WikiTyp::updateOrCreate(
                ['klucz' => $typ['klucz']],
                [
                    'etykieta' => $typ['etykieta'],
                    'pola' => $typ['pola'],
                    'lead' => $typ['lead'],
                    'sekcje' => $typ['sekcje'],
                    'kolejnosc' => $i,
                ],
            );
        }
    }
}
