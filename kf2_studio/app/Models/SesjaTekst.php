<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SesjaTekst extends Model
{
    protected $table = 'sesje_teksty';

    protected $fillable = ['rodzaj', 'tresc', 'kolejnosc'];
}
