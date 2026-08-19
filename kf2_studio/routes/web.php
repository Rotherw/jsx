<?php

use App\Http\Controllers\ListingiController;
use App\Http\Controllers\SesjeController;
use App\Http\Controllers\WikiController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/wiki')->name('start');

Route::controller(WikiController::class)->prefix('wiki')->name('wiki.')->group(function (): void {
    Route::get('/', 'index')->name('index');
    Route::post('/', 'generuj')->name('generuj');
    Route::post('/zapisz', 'zapisz')->name('zapisz');
});

Route::controller(SesjeController::class)->prefix('sesje')->name('sesje.')->group(function (): void {
    Route::get('/', 'index')->name('index');
    Route::post('/', 'generuj')->name('generuj');
    Route::post('/zapisz', 'zapisz')->name('zapisz');
});

Route::controller(ListingiController::class)->prefix('listingi')->name('listingi.')->group(function (): void {
    Route::get('/', 'index')->name('index');
    Route::post('/', 'zapisz')->name('utworz');
    Route::get('/{produkt}', 'pokaz')->name('pokaz');
    Route::put('/{produkt}', 'zapisz')->name('zapisz');
    Route::get('/{produkt}/paczka', 'paczka')->name('paczka');
    Route::get('/{produkt}/eksport/{platforma}', 'eksport')->name('eksport');
});
