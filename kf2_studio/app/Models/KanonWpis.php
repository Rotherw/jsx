<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class KanonWpis extends Model
{
    protected $table = 'kanon_wpisy';

    protected $fillable = ['kategoria', 'wartosc', 'kolejnosc'];
}
