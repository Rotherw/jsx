<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class KanonFakt extends Model
{
    protected $table = 'kanon_fakty';

    protected $fillable = ['klucz', 'etykieta', 'wartosc', 'kolejnosc'];
}
