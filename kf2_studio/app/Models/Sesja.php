<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Sesja extends Model
{
    protected $table = 'sesje';

    protected $fillable = ['tytul', 'rodzaj', 'wejscie', 'ziarno', 'wskazowki_mg', 'tresc'];

    protected function casts(): array
    {
        return ['wejscie' => 'array', 'wskazowki_mg' => 'boolean', 'ziarno' => 'integer'];
    }
}
