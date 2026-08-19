<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Platforma extends Model
{
    protected $table = 'platformy';

    protected $fillable = [
        'slug', 'nazwa', 'jezyk', 'limit_tytulu', 'limit_opisu', 'limit_tagow',
        'format_tagu', 'markdown', 'linki_zewnetrzne', 'uwagi', 'kolejnosc',
    ];

    protected function casts(): array
    {
        return ['markdown' => 'boolean', 'linki_zewnetrzne' => 'boolean'];
    }

    public function listingi(): HasMany
    {
        return $this->hasMany(Listing::class, 'platforma_id');
    }
}
