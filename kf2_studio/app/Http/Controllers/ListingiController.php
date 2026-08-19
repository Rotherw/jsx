<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Models\Platforma;
use App\Models\Produkt;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ListingiController extends Controller
{
    public function __construct(
        private readonly ListingExporter $exporter,
        private readonly ListingLinter $linter,
    ) {}

    public function index(): View
    {
        $produkty = Produkt::orderBy('sku')->get();

        // Uwagi lintera liczone na biezaco - zawsze odbijaja aktualna tresc.
        $uwagi = $produkty->mapWithKeys(
            fn (Produkt $produkt): array => [$produkt->id => $this->linter->sprawdz($produkt->doEksportu())],
        );

        return view('listingi.index', [
            'produkty' => $produkty,
            'uwagi' => $uwagi,
            'platformy' => Platforma::orderBy('kolejnosc')->get(),
        ]);
    }

    public function pokaz(Produkt $produkt): View
    {
        return view('listingi.pokaz', [
            'produkt' => $produkt,
            'uwagi' => $this->linter->sprawdz($produkt->doEksportu()),
            'eksporty' => $this->exporter->wszystkie($produkt->doEksportu()),
        ]);
    }

    public function zapisz(Request $request, ?Produkt $produkt = null): RedirectResponse
    {
        $dane = $request->validate([
            'sku' => ['required', 'string', 'max:100'],
            'tytul_pl' => ['nullable', 'string', 'max:250'],
            'tytul_en' => ['nullable', 'string', 'max:250'],
            'opis_pl' => ['nullable', 'string', 'max:20000'],
            'opis_en' => ['nullable', 'string', 'max:20000'],
            'tagi' => ['nullable', 'string', 'max:2000'],
            'status' => ['nullable', 'string', 'max:50'],
        ]);

        $dane['tagi'] = collect(explode(',', (string) ($dane['tagi'] ?? '')))
            ->map(static fn (string $tag): string => trim($tag))
            ->filter()
            ->values()
            ->all();

        $produkt = $produkt?->exists
            ? tap($produkt)->update($dane)
            : Produkt::create($dane);

        return redirect()
            ->route('listingi.pokaz', $produkt)
            ->with('info', 'Produkt zapisany.');
    }

    /** Eksport pod jedna platforme jako plik do wklejenia / zaimportowania. */
    public function eksport(Produkt $produkt, string $platforma): StreamedResponse
    {
        $eksport = $this->exporter->dlaPlatformy($produkt->doEksportu(), $platforma);

        $tresc = json_encode($eksport, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $nazwaPliku = "{$produkt->sku}-{$platforma}.json";

        return response()->streamDownload(
            static function () use ($tresc): void {
                echo $tresc;
            },
            $nazwaPliku,
            ['Content-Type' => 'application/json; charset=utf-8'],
        );
    }
}
