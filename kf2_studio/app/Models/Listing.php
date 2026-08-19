<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * Wiersz dystrybucji: jeden produkt na jednej platformie (sekcja 7).
 */
class Listing extends Model
{
    protected $table = 'listingi';

    protected $fillable = [
        'produkt_id', 'platforma_id', 'status', 'data_publikacji', 'link',
        'wersja_plikow', 'cover', 'film', 'powiazany_post', 'ostatni_eksport',
    ];

    protected function casts(): array
    {
        return [
            'ostatni_eksport' => 'array',
            'data_publikacji' => 'datetime',
        ];
    }

    public function produkt(): BelongsTo
    {
        return $this->belongsTo(Produkt::class, 'produkt_id');
    }

    public function platforma(): BelongsTo
    {
        return $this->belongsTo(Platforma::class, 'platforma_id');
    }

    /**
     * Sekcja 13: publikacje uznajemy za wykonana dopiero po otrzymaniu
     * dzialajacego linku - sam status nie wystarcza.
     */
    public function opublikowany(): bool
    {
        return in_array($this->status, ['UPLOADED', 'PUBLISHED'], true)
            && trim((string) $this->link) !== '';
    }
}
