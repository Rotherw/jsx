<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class WikiArtykul extends Model
{
    protected $table = 'wiki_artykuly';

    protected $fillable = ['typ_klucz', 'nazwa', 'ton', 'format', 'ze_stopka', 'dane', 'tresc', 'ma_luki'];

    protected function casts(): array
    {
        return ['dane' => 'array', 'ze_stopka' => 'boolean', 'ma_luki' => 'boolean'];
    }
}
