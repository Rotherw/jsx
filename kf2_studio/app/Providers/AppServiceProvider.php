<?php

declare(strict_types=1);

namespace App\Providers;

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Domain\SessionGenerator;
use App\Domain\WikiGenerator;
use App\Support\Kanon;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(Kanon::class);

        // Generatory dostaja dane z bazy; pliki w database/data sluza tylko
        // do zasiania i jako awaryjne zrodlo, gdy migracje jeszcze nie poszly.
        $this->app->singleton(WikiGenerator::class, static fn ($app): WikiGenerator => new WikiGenerator(
            $app->make(Kanon::class)->typyWiki(),
        ));

        $this->app->singleton(SessionGenerator::class, static fn ($app): SessionGenerator => new SessionGenerator(
            $app->make(Kanon::class)->slownikSesji(),
        ));

        $this->app->singleton(ListingExporter::class, static fn ($app): ListingExporter => new ListingExporter(
            $app->make(Kanon::class)->platformy(),
        ));

        $this->app->singleton(ListingLinter::class);
    }

    public function boot(): void
    {
        //
    }
}
