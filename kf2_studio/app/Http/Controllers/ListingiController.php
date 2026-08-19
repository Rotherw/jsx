<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Domain\Listing\ListingExporter;
use App\Domain\Listing\ListingLinter;
use App\Models\Platforma;
use App\Models\Produkt;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Illuminate\View\View;
use RuntimeException;
use Symfony\Component\HttpFoundation\StreamedResponse;
use ZipArchive;

class ListingiController extends Controller
{
    public function __construct(
        private readonly ListingExporter $exporter,
        private readonly ListingLinter $linter,
    ) {}

    public function index(): View
    {
        $produkty = Produkt::with('listingi')->orderBy('sku')->get();

        // Uwagi liczone na biezaco - zawsze odbijaja aktualna tresc rejestru.
        $uwagi = $produkty->mapWithKeys(
            fn (Produkt $produkt): array => [$produkt->id => $this->linter->sprawdz($produkt->doRejestru())],
        );

        return view('listingi.index', [
            'produkty' => $produkty,
            'uwagi' => $uwagi,
            'linter' => $this->linter,
            'platformy' => Platforma::orderBy('priorytet')->get(),
        ]);
    }

    public function pokaz(Produkt $produkt): View
    {
        $produkt->load('listingi.platforma');
        $rejestr = $produkt->doRejestru();

        return view('listingi.pokaz', [
            'produkt' => $produkt,
            'uwagi' => $this->linter->sprawdz($rejestr),
            'linter' => $this->linter,
            'eksporty' => $this->exporter->wszystkie($rejestr),
            'statusy' => Produkt::STATUSY,
        ]);
    }

    public function zapisz(Request $request, ?Produkt $produkt = null): RedirectResponse
    {
        $istnieje = $produkt !== null && $produkt->exists;
        $dane = $this->waliduj($request, $istnieje ? $produkt : null);

        $dane['tagi'] = $this->rozbijTagi((string) ($dane['tagi'] ?? ''));
        $dane['formaty'] = $this->rozbijTagi((string) ($dane['formaty'] ?? ''));

        if ($istnieje) {
            // SKU jest niezmienne - model rzuci wyjatkiem, wiec nie podajemy go dalej.
            unset($dane['sku']);
            $produkt->update($dane);
        } else {
            $produkt = Produkt::create($dane);
        }

        return redirect()
            ->route('listingi.pokaz', $produkt)
            ->with('info', 'Wpis rejestru zapisany.');
    }

    /** Eksport tekstow pod jedna platforme. */
    public function eksport(Produkt $produkt, string $platforma): StreamedResponse
    {
        $eksport = $this->exporter->dlaPlatformy($produkt->doRejestru(), $platforma);

        $tresc = json_encode($eksport, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

        return response()->streamDownload(
            static function () use ($tresc): void {
                echo $tresc;
            },
            "{$produkt->sku}-{$platforma}.json",
            ['Content-Type' => 'application/json; charset=utf-8'],
        );
    }

    /**
     * Komplet plikow katalogu 06_THANGS_LISTING z paczki Commander V3,
     * spakowany tak, zeby dalo sie go wrzucic wprost do folderu produktu.
     */
    public function paczka(Produkt $produkt): StreamedResponse
    {
        $pliki = $this->exporter->plikiPaczki($produkt->doRejestru());
        $sciezka = tempnam(sys_get_temp_dir(), 'kf2-listing-');

        if ($sciezka === false) {
            throw new RuntimeException('Nie udalo sie utworzyc pliku tymczasowego.');
        }

        $zip = new ZipArchive();
        if ($zip->open($sciezka, ZipArchive::OVERWRITE) !== true) {
            throw new RuntimeException('Nie udalo sie otworzyc archiwum do zapisu.');
        }

        foreach ($pliki as $nazwa => $tresc) {
            $zip->addFromString("06_THANGS_LISTING/{$nazwa}", $tresc);
        }
        $zip->close();

        return response()->streamDownload(
            static function () use ($sciezka): void {
                readfile($sciezka);
                @unlink($sciezka);
            },
            "{$produkt->sku}-06_THANGS_LISTING.zip",
            ['Content-Type' => 'application/zip'],
        );
    }

    /** @return array<string, mixed> */
    private function waliduj(Request $request, ?Produkt $istniejacy): array
    {
        $regulySku = ['required', 'string', 'max:100'];
        if ($istniejacy === null) {
            $regulySku[] = 'unique:produkty,sku';
        }

        return Validator::make($request->all(), [
            'sku' => $regulySku,
            'nazwa_pl' => ['nullable', 'string', 'max:250'],
            'nazwa_en' => ['nullable', 'string', 'max:250'],
            'tytul_sprzedazowy' => ['nullable', 'string', 'max:250'],
            'tytul_krotki' => ['nullable', 'string', 'max:250'],
            'slug' => ['nullable', 'string', 'max:250'],
            'typ_produktu' => ['nullable', 'string', 'max:100'],
            'kolekcja' => ['nullable', 'string', 'max:150'],
            'wersja' => ['nullable', 'string', 'max:50'],
            'swiat' => ['nullable', 'string', 'max:50'],
            'lokacja' => ['nullable', 'string', 'max:150'],
            'frakcja' => ['nullable', 'string', 'max:150'],
            'postac' => ['nullable', 'string', 'max:150'],
            'zrodlo_lore' => ['nullable', 'string', 'max:250'],
            'link_lore' => ['nullable', 'string', 'max:500'],
            'formaty' => ['nullable', 'string', 'max:500'],
            'liczba_elementow' => ['nullable', 'integer', 'min:1'],
            'skala' => ['nullable', 'string', 'max:100'],
            'technologia' => ['nullable', 'string', 'max:100'],
            'ustawienia_druku' => ['nullable', 'string', 'max:2000'],
            'stan_testu' => ['nullable', 'string', 'max:150'],
            'wymaga_podpor' => ['nullable', 'boolean'],
            'data_przygotowania' => ['nullable', 'date'],
            'cena' => ['nullable', 'numeric', 'min:0'],
            'platny' => ['nullable', 'boolean'],
            'licencja_podstawowa' => ['nullable', 'string', 'max:150'],
            'licencja_komercyjna' => ['nullable', 'string', 'max:150'],
            'limit_sprzedazy' => ['nullable', 'string', 'max:150'],
            'zawartosc_zestawu' => ['nullable', 'string', 'max:2000'],
            'krotki_opis' => ['nullable', 'string', 'max:1000'],
            'opis_pl' => ['nullable', 'string', 'max:20000'],
            'opis_en' => ['nullable', 'string', 'max:20000'],
            'opis_cc_cn' => ['nullable', 'string', 'max:20000'],
            'tagi' => ['nullable', 'string', 'max:2000'],
            'tytul_posta' => ['nullable', 'string', 'max:250'],
            'cta' => ['nullable', 'string', 'max:1000'],
            'status' => ['nullable', 'in:'.implode(',', Produkt::STATUSY)],
        ])->validate();
    }

    /** @return array<int, string> */
    private function rozbijTagi(string $surowe): array
    {
        return collect(explode(',', $surowe))
            ->map(static fn (string $tag): string => trim($tag))
            ->filter()
            ->values()
            ->all();
    }
}
