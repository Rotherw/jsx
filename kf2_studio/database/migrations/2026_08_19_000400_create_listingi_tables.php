<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Rejestr modeli - "source of truth" z sekcji 7 systemu operacyjnego v2.0.
 * Uklad pol i statusow odwzorowuje dokument, zeby rejestr dalo sie porownac
 * z papierem 1:1.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('platformy', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->string('slug')->unique();
            $tabela->string('nazwa');
            // Sufiks plikow w paczce: DESCRIPTION_<kod>.txt, TAGS_<kod>.txt.
            $tabela->string('kod_pliku');
            $tabela->string('jezyk', 5)->default('en');
            // Zestaw domyslny vs "tylko na osobne polecenie" (sekcja 13).
            $tabela->boolean('domyslna')->default(false)->index();
            $tabela->unsignedSmallInteger('priorytet')->default(99);
            $tabela->unsignedSmallInteger('limit_tytulu')->default(100);
            $tabela->unsignedInteger('limit_opisu')->default(5000);
            $tabela->unsignedSmallInteger('limit_tagow')->default(10);
            // Dopoki false, limit jest orientacyjny - sekcja 13 zabrania
            // opierac sie slepo na starych limitach tagow.
            $tabela->boolean('limity_potwierdzone')->default(false);
            $tabela->string('format_tagu')->default('swobodny');
            $tabela->boolean('markdown')->default(false);
            $tabela->boolean('linki_zewnetrzne')->default(true);
            $tabela->text('uwagi')->nullable();
            $tabela->timestamps();
        });

        Schema::create('produkty', function (Blueprint $tabela): void {
            $tabela->id();

            // --- TOZSAMOSC ---
            // SKU po nadaniu nie zmienia sie i nie moze zostac uzyte ponownie.
            $tabela->string('sku')->unique();
            $tabela->string('nazwa_pl')->nullable();
            $tabela->string('nazwa_en')->nullable();
            $tabela->string('tytul_sprzedazowy')->nullable();
            // Skrocony tytul platformowy (komplet metadanych, p. 4).
            $tabela->string('tytul_krotki')->nullable();
            $tabela->string('slug')->nullable();
            $tabela->string('typ_produktu')->nullable();
            $tabela->string('kolekcja')->nullable();
            $tabela->string('wersja')->default('v1');

            // --- SWIAT ---
            $tabela->string('swiat')->default('kf2')->index();
            $tabela->string('lokacja')->nullable();
            $tabela->string('frakcja')->nullable();
            $tabela->string('postac')->nullable();
            $tabela->string('zrodlo_lore')->nullable();
            $tabela->string('link_lore')->nullable();

            // --- PRODUKCJA ---
            $tabela->json('formaty')->nullable();
            $tabela->unsignedSmallInteger('liczba_elementow')->nullable();
            $tabela->string('skala')->nullable();
            $tabela->string('technologia')->nullable();
            $tabela->text('ustawienia_druku')->nullable();
            // null = nieprzetestowane. Sekcja 10 zabrania deklarowac test druku,
            // ktorego nie bylo.
            $tabela->string('stan_testu')->nullable();
            $tabela->boolean('wymaga_podpor')->nullable();
            $tabela->date('data_przygotowania')->nullable();

            // --- SPRZEDAZ ---
            $tabela->decimal('cena', 8, 2)->nullable();
            $tabela->boolean('platny')->default(true);
            $tabela->string('licencja_podstawowa')->nullable();
            $tabela->string('licencja_komercyjna')->nullable();
            $tabela->string('limit_sprzedazy')->nullable();
            $tabela->text('zawartosc_zestawu')->nullable();

            // --- TRESCI LISTINGU ---
            $tabela->text('krotki_opis')->nullable();
            $tabela->text('opis_pl')->nullable();
            $tabela->text('opis_en')->nullable();
            // Osobno redagowany, nie tlumaczony automatycznie (metadane, p. 10).
            $tabela->text('opis_cc_cn')->nullable();
            $tabela->json('tagi')->default('[]');
            $tabela->string('tytul_posta')->nullable();
            $tabela->text('cta')->nullable();

            $tabela->string('status')->default('SOURCE')->index();
            $tabela->timestamps();
        });

        // Dystrybucja: jeden wiersz na parę produkt-platforma.
        Schema::create('listingi', function (Blueprint $tabela): void {
            $tabela->id();
            $tabela->foreignId('produkt_id')->constrained('produkty')->cascadeOnDelete();
            $tabela->foreignId('platforma_id')->constrained('platformy')->cascadeOnDelete();
            $tabela->string('status')->default('SOURCE')->index();
            $tabela->timestamp('data_publikacji')->nullable();
            // Publikacje uznajemy za wykonana dopiero po dzialajacym linku.
            $tabela->string('link')->nullable();
            $tabela->string('wersja_plikow')->nullable();
            $tabela->string('cover')->nullable();
            $tabela->string('film')->nullable();
            $tabela->string('powiazany_post')->nullable();
            $tabela->json('ostatni_eksport')->nullable();
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
