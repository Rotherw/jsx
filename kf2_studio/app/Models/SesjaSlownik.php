<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SesjaSlownik extends Model
{
    protected $table = 'sesje_slowniki';

    protected $fillable = ['rodzaj', 'klucz', 'etykieta', 'atrybuty', 'kolejnosc'];

    protected function casts(): array
    {
        return ['atrybuty' => 'array'];
    }
}
