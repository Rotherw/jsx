<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Szkielety artykulow - edytowalne bez wdrozenia kodu.
        Schema::create('wiki_typy', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('klucz')->unique();
            $tabela->string('etykieta');
            $tabela->json('pola');
            $tabela->json('lead');
            $tabela->json('sekcje');
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();
        });

        Schema::create('wiki_artykuly', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('typ_klucz')->index();
            $tabela->string('nazwa');
            $tabela->string('ton')->default('domyslny');
            $tabela->string('format')->default('wiki');
            $tabela->boolean('ze_stopka')->default(false);
            $tabela->json('dane');
            $tabela->text('tresc');
            // Artykul z lukami nie jest gotowy do wklejenia na wiki.
            $tabela->boolean('ma_luki')->default(true)->index();
            $tabela->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('wiki_artykuly');
        Schema::dropIfExists('wiki_typy');
    }
};
