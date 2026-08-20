<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class WikiTyp extends Model
{
    protected $table = 'wiki_typy';

    protected $fillable = ['klucz', 'etykieta', 'pola', 'lead', 'sekcje', 'kolejnosc'];

    protected function casts(): array
    {
        return ['pola' => 'array', 'lead' => 'array', 'sekcje' => 'array'];
    }
}
