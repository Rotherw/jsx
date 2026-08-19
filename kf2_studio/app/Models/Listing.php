<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Listing extends Model
{
    protected $table = 'listingi';

    protected $fillable = ['produkt_id', 'platforma_id', 'url', 'status', 'ostatni_eksport', 'opublikowano_at'];

    protected function casts(): array
    {
        return ['ostatni_eksport' => 'array', 'opublikowano_at' => 'datetime'];
    }

    public function produkt(): BelongsTo
    {
        return $this->belongsTo(Produkt::class, 'produkt_id');
    }

    public function platforma(): BelongsTo
    {
        return $this->belongsTo(Platforma::class, 'platforma_id');
    }
}
