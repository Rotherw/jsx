<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use RuntimeException;

/**
 * Wpis rejestru modeli - "source of truth" z sekcji 7 systemu v2.0.
 */
class Produkt extends Model
{
    /** Statusy z sekcji 7. Kolejnosc odpowiada postepowi wydania. */
    public const STATUSY = [
        'SOURCE', 'IN_PROGRESS', 'READY_TO_UPLOAD', 'UPLOADED',
        'PUBLISHED', 'NEEDS_UPDATE', 'ARCHIVED',
    ];

    protected $table = 'produkty';

    protected $fillable = [
        'sku', 'nazwa_pl', 'nazwa_en', 'tytul_sprzedazowy', 'tytul_krotki', 'slug',
        'typ_produktu', 'kolekcja', 'wersja',
        'swiat', 'lokacja', 'frakcja', 'postac', 'zrodlo_lore', 'link_lore',
        'formaty', 'liczba_elementow', 'skala', 'technologia', 'ustawienia_druku',
        'stan_testu', 'wymaga_podpor', 'data_przygotowania',
        'cena', 'platny', 'licencja_podstawowa', 'licencja_komercyjna',
        'limit_sprzedazy', 'zawartosc_zestawu',
        'krotki_opis', 'opis_pl', 'opis_en', 'opis_cc_cn', 'tagi',
        'tytul_posta', 'cta', 'status',
    ];

    protected function casts(): array
    {
        return [
            'formaty' => 'array',
            'tagi' => 'array',
            'platny' => 'boolean',
            'wymaga_podpor' => 'boolean',
            'data_przygotowania' => 'date',
            'cena' => 'decimal:2',
            'liczba_elementow' => 'integer',
        ];
    }

    protected static function booted(): void
    {
        // Sekcja 7: SKU po nadaniu nie zmienia sie i nie moze zostac uzyte ponownie.
        static::updating(function (self $produkt): void {
            if ($produkt->isDirty('sku')) {
                throw new RuntimeException(
                    'SKU jest niezmienne po nadaniu (system v2.0, sekcja 7). '
                    .'Aby wycofac produkt, ustaw status ARCHIVED i nadaj nowe SKU.',
                );
            }
        });
    }

    public function listingi(): HasMany
    {
        return $this->hasMany(Listing::class, 'produkt_id');
    }

    /**
     * Ksztalt oczekiwany przez App\Domain\Listing\*.
     *
     * @return array<string, mixed>
     */
    public function doRejestru(): array
    {
        $dane = $this->only($this->fillable);
        // Kontrola "PUBLISHED bez linku" potrzebuje wiedzy, czy gdziekolwiek
        // jest juz dzialajaca oferta.
        $dane['link'] = $this->pierwszyLink();

        return $dane;
    }

    public function pierwszyLink(): string
    {
        $listingi = $this->relationLoaded('listingi')
            ? $this->getRelation('listingi')
            : $this->listingi()->whereNotNull('link')->get();

        foreach ($listingi as $listing) {
            if (trim((string) $listing->link) !== '') {
                return (string) $listing->link;
            }
        }

        return '';
    }
}
