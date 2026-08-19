<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('sesje_motywy', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('klucz')->unique();
            $tabela->string('etykieta');
            $tabela->json('tytuly');
            $tabela->json('zaczepki');
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();
        });

        // Tony, skale, dlugosci i rodzaje - jedna tabela, rozroznienie po "rodzaj".
        Schema::create('sesje_slowniki', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('rodzaj')->index();
            $tabela->string('klucz');
            $tabela->string('etykieta');
            $tabela->json('atrybuty')->nullable();
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();

            $tabela->unique(['rodzaj', 'klucz']);
        });

        // Komplikacje, kulminacje, zakonczenia, wskazowki dla prowadzacego.
        Schema::create('sesje_teksty', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('rodzaj')->index();
            $tabela->text('tresc');
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();
        });

        Schema::create('sesje', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('tytul');
            $tabela->string('rodzaj')->default('fg')->index();
            $tabela->json('wejscie');
            // Ziarno pozwala odtworzyc dokladnie ten sam szkielet.
            $tabela->bigInteger('ziarno');
            $tabela->boolean('wskazowki_mg')->default(true);
            $tabela->text('tresc');
            $tabela->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('sesje');
        Schema::dropIfExists('sesje_teksty');
        Schema::dropIfExists('sesje_slowniki');
        Schema::dropIfExists('sesje_motywy');
    }
};
