<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Domain\Template;
use App\Domain\WikiGenerator;
use App\Models\WikiArtykul;
use App\Support\Kanon;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class WikiController extends Controller
{
    public function __construct(
        private readonly WikiGenerator $generator,
        private readonly Kanon $kanon,
    ) {}

    public function index(): View
    {
        return view('wiki.index', [
            'typy' => $this->generator->typy(),
            'kanon' => $this->kanon,
            'artykuly' => WikiArtykul::latest()->limit(20)->get(),
            'wynik' => null,
            'wejscie' => [],
        ]);
    }

    public function generuj(Request $request): View
    {
        $dane = $request->validate([
            'typ' => ['required', 'string'],
            'nazwa' => ['nullable', 'string', 'max:200'],
            'kontynent' => ['nullable', 'string', 'max:100'],
            'panstwo' => ['nullable', 'string', 'max:100'],
            'rasa' => ['nullable', 'string', 'max:100'],
            'rola' => ['nullable', 'string', 'max:200'],
            'charakter' => ['nullable', 'string', 'max:100'],
            'rok' => ['nullable', 'string', 'max:100'],
            'zarys' => ['nullable', 'string', 'max:5000'],
            'ton' => ['nullable', 'string'],
            'format' => ['nullable', 'in:wiki,tekst'],
            'ze_stopka' => ['nullable', 'boolean'],
        ]);

        $tresc = $this->generator->generuj(
            $dane['typ'],
            $dane,
            $dane['ton'] ?? 'domyslny',
            $dane['format'] ?? WikiGenerator::FORMAT_WIKI,
            (bool) ($dane['ze_stopka'] ?? false),
        );

        return view('wiki.index', [
            'typy' => $this->generator->typy(),
            'kanon' => $this->kanon,
            'artykuly' => WikiArtykul::latest()->limit(20)->get(),
            'wynik' => $tresc,
            'wejscie' => $dane,
        ]);
    }

    public function zapisz(Request $request): RedirectResponse
    {
        $dane = $request->validate([
            'typ' => ['required', 'string'],
            'nazwa' => ['required', 'string', 'max:200'],
            'tresc' => ['required', 'string'],
            'ton' => ['nullable', 'string'],
            'format' => ['nullable', 'in:wiki,tekst'],
            'ze_stopka' => ['nullable', 'boolean'],
        ]);

        WikiArtykul::create([
            'typ_klucz' => $dane['typ'],
            'nazwa' => $dane['nazwa'],
            'ton' => $dane['ton'] ?? 'domyslny',
            'format' => $dane['format'] ?? WikiGenerator::FORMAT_WIKI,
            'ze_stopka' => (bool) ($dane['ze_stopka'] ?? false),
            'dane' => $request->except(['_token', 'tresc']),
            'tresc' => $dane['tresc'],
            'ma_luki' => Template::maLuki($dane['tresc']),
        ]);

        return redirect()->route('wiki.index')->with('info', 'Artykuł zapisany w bazie.');
    }
}
