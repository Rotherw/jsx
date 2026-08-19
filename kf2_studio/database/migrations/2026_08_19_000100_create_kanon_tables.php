<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Skrot kanonu pokazywany w zakladce "Kanon" obu generatorow.
        Schema::create('kanon_fakty', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('klucz')->unique();
            $tabela->string('etykieta');
            $tabela->text('wartosc');
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();
        });

        // Listy wyboru: panstwa, rasy, kontynenty, ksiestwa, lokacje, charaktery.
        Schema::create('kanon_wpisy', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('kategoria')->index();
            $tabela->string('wartosc');
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();

            $tabela->unique(['kategoria', 'wartosc']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('kanon_wpisy');
        Schema::dropIfExists('kanon_fakty');
    }
};
