<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('platformy', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('slug')->unique();
            $tabela->string('nazwa');
            $tabela->string('jezyk', 5)->default('en');
            $tabela->unsignedSmallInteger('limit_tytulu')->default(100);
            $tabela->unsignedInteger('limit_opisu')->default(5000);
            $tabela->unsignedSmallInteger('limit_tagow')->default(10);
            $tabela->string('format_tagu')->default('swobodny');
            $tabela->boolean('markdown')->default(false);
            $tabela->boolean('linki_zewnetrzne')->default(true);
            $tabela->text('uwagi')->nullable();
            $tabela->unsignedSmallInteger('kolejnosc')->default(0);
            $tabela->timestamps();
        });

        // Jedno zrodlo prawdy dla tytulow, opisow i tagow wszystkich modeli.
        Schema::create('produkty', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('sku')->unique();
            $tabela->string('tytul_pl')->nullable();
            $tabela->string('tytul_en')->nullable();
            $tabela->text('opis_pl')->nullable();
            $tabela->text('opis_en')->nullable();
            $tabela->json('tagi')->default('[]');
            $tabela->string('status')->default('szkic')->index();
            $tabela->timestamps();
        });

        // Stan publikacji danego produktu na danej platformie.
        Schema::create('listingi', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->foreignId('produkt_id')->constrained('produkty')->cascadeOnDelete();
            $tabela->foreignId('platforma_id')->constrained('platformy')->cascadeOnDelete();
            $tabela->string('url')->nullable();
            $tabela->string('status')->default('nieopublikowany')->index();
            $tabela->json('ostatni_eksport')->nullable();
            $tabela->timestamp('opublikowano_at')->nullable();
            $tabela->timestamps();

            $tabela->unique(['produkt_id', 'platforma_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('listingi');
        Schema::dropIfExists('produkty');
        Schema::dropIfExists('platformy');
    }
};
