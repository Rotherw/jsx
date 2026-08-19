<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SesjaMotyw extends Model
{
    protected $table = 'sesje_motywy';

    protected $fillable = ['klucz', 'etykieta', 'tytuly', 'zaczepki', 'kolejnosc'];

    protected function casts(): array
    {
        return ['tytuly' => 'array', 'zaczepki' => 'array'];
    }
}
