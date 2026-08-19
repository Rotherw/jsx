<?php

use Illuminate\Support\Facades\Artisan;

Artisan::command('kf2:smoke', function (): int {
    $this->info('Test dymny rdzenia generatorow (bez bazy):');
    passthru(PHP_BINARY.' '.base_path('tools/smoke.php'), $kod);

    return $kod;
})->purpose('Uruchamia testy dymne generatorow KF2');
