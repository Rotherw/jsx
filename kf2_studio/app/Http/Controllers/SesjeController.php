<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Domain\SessionGenerator;
use App\Models\Sesja;
use App\Support\Kanon;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class SesjeController extends Controller
{
    public function __construct(
        private readonly SessionGenerator $generator,
        private readonly Kanon $kanon,
    ) {}

    public function index(): View
    {
        return $this->widok(null, [], null);
    }

    public function generuj(Request $request): View
    {
        $dane = $this->waliduj($request);

        // Puste ziarno = nowy wariant. Podane ziarno = odtworzenie tego samego.
        $ziarno = $request->filled('ziarno')
            ? (int) $request->input('ziarno')
            : $this->generator->losoweZiarno();

        $tresc = $this->generator->generuj($dane, $ziarno, (bool) ($dane['wskazowki_mg'] ?? true));

        return $this->widok($tresc, $dane, $ziarno);
    }

    public function zapisz(Request $request): RedirectResponse
    {
        $dane = $this->waliduj($request);
        $walidacja = $request->validate([
            'tytul_wyniku' => ['required', 'string', 'max:200'],
            'ziarno' => ['required', 'integer'],
            'tresc' => ['required', 'string'],
        ]);

        Sesja::create([
            'tytul' => $walidacja['tytul_wyniku'],
            'rodzaj' => $dane['rodzaj'] ?? 'fg',
            'wejscie' => $dane,
            'ziarno' => (int) $walidacja['ziarno'],
            'wskazowki_mg' => (bool) ($dane['wskazowki_mg'] ?? true),
            'tresc' => $walidacja['tresc'],
        ]);

        return redirect()->route('sesje.index')->with('info', 'Sesja zapisana w bazie.');
    }

    /** @return array<string, mixed> */
    private function waliduj(Request $request): array
    {
        return $request->validate([
            'tytul' => ['nullable', 'string', 'max:200'],
            'rodzaj' => ['nullable', 'string'],
            'skala' => ['nullable', 'string'],
            'dlugosc' => ['nullable', 'string'],
            'motywy' => ['nullable', 'array', 'max:2'],
            'motywy.*' => ['string'],
            'panstwo' => ['nullable', 'string', 'max:100'],
            'miejsce' => ['nullable', 'string', 'max:100'],
            'frakcja' => ['nullable', 'string', 'max:100'],
            'ton' => ['nullable', 'string'],
            'fabula' => ['nullable', 'string', 'max:5000'],
            'wskazowki_mg' => ['nullable', 'boolean'],
        ]);
    }

    /** @param array<string, mixed> $wejscie */
    private function widok(?string $wynik, array $wejscie, ?int $ziarno): View
    {
        return view('sesje.index', [
            'slownik' => $this->generator->slownik(),
            'kanon' => $this->kanon,
            'sesje' => Sesja::latest()->limit(20)->get(),
            'wynik' => $wynik,
            'wejscie' => $wejscie,
            'ziarno' => $ziarno,
        ]);
    }
}
