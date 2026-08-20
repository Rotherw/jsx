<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Platforma extends Model
{
    protected $table = 'platformy';

    protected $fillable = [
        'slug', 'nazwa', 'kod_pliku', 'jezyk', 'domyslna', 'priorytet',
        'limit_tytulu', 'limit_opisu', 'limit_tagow', 'limity_potwierdzone',
        'format_tagu', 'markdown', 'linki_zewnetrzne', 'uwagi',
    ];

    protected function casts(): array
    {
        return [
            'domyslna' => 'boolean',
            'limity_potwierdzone' => 'boolean',
            'markdown' => 'boolean',
            'linki_zewnetrzne' => 'boolean',
        ];
    }

    /** Zestaw obslugiwany domyslnie (sekcja 13), w kolejnosci priorytetu. */
    public function scopeDomyslne(Builder $zapytanie): Builder
    {
        return $zapytanie->where('domyslna', true)->orderBy('priorytet');
    }

    public function listingi(): HasMany
    {
        return $this->hasMany(Listing::class, 'platforma_id');
    }
}
