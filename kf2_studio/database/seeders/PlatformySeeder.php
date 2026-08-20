<?php

declare(strict_types=1);

namespace Database\Seeders;

use App\Models\Platforma;
use Illuminate\Database\Seeder;

class PlatformySeeder extends Seeder
{
    public function run(): void
    {
        foreach (require database_path('data/platforms.php') as $platforma) {
            Platforma::updateOrCreate(
                ['slug' => $platforma['slug']],
                [
                    'nazwa' => $platforma['nazwa'],
                    'kod_pliku' => $platforma['kod_pliku'],
                    'jezyk' => $platforma['jezyk'],
                    'domyslna' => $platforma['domyslna'],
                    'priorytet' => $platforma['priorytet'],
                    'limit_tytulu' => $platforma['limit_tytulu'],
                    'limit_opisu' => $platforma['limit_opisu'],
                    'limit_tagow' => $platforma['limit_tagow'],
                    'limity_potwierdzone' => $platforma['limity_potwierdzone'],
                    'format_tagu' => $platforma['format_tagu'],
                    'markdown' => $platforma['markdown'],
                    'linki_zewnetrzne' => $platforma['linki_zewnetrzne'] ?? true,
                    'uwagi' => $platforma['uwagi'] ?? null,
                ],
            );
        }
    }
}
