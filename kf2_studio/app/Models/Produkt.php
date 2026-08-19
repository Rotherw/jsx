<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Produkt extends Model
{
    protected $table = 'produkty';

    protected $fillable = ['sku', 'tytul_pl', 'tytul_en', 'opis_pl', 'opis_en', 'tagi', 'status'];

    protected function casts(): array
    {
        return ['tagi' => 'array'];
    }

    public function listingi(): HasMany
    {
        return $this->hasMany(Listing::class, 'produkt_id');
    }

    /** Ksztalt oczekiwany przez App\Domain\Listing\*. */
    public function doEksportu(): array
    {
        return [
            'tytul_pl' => (string) $this->tytul_pl,
            'tytul_en' => (string) $this->tytul_en,
            'opis_pl' => (string) $this->opis_pl,
            'opis_en' => (string) $this->opis_en,
            'tagi' => $this->tagi ?? [],
        ];
    }
}
