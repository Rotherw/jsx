<?php

declare(strict_types=1);

namespace App\Domain;

use InvalidArgumentException;

/**
 * Generator szkieletow sesji (Opowiesci Fallathanu).
 *
 * W odroznieniu od wersji HTML losowanie jest deterministyczne: kazdy wynik
 * ma ziarno (seed), ktore zapisujemy razem z sesja. Ten sam zestaw wejsc
 * i to samo ziarno zawsze daje ten sam szkielet - dzieki temu zapisana
 * sesja da sie odtworzyc, a nie tylko przechowac jako tekst.
 */
final class SessionGenerator
{
    /** @param array<string, mixed> $dane zawartosc database/data/session_data.php */
    public function __construct(private readonly array $dane) {}

    /** @return array<string, mixed> */
    public function slownik(): array
    {
        return $this->dane;
    }

    public function losoweZiarno(): int
    {
        return random_int(1, PHP_INT_MAX);
    }

    /**
     * @param array<string, mixed> $wejscie tytul, rodzaj, skala, motywy[], panstwo,
     *                                      miejsce, frakcja, dlugosc, ton, fabula
     */
    public function generuj(array $wejscie, int $ziarno, bool $wskazowkiMg = true): string
    {
        $los = new Losowanie($ziarno);

        $motywy = array_values(array_filter((array) ($wejscie['motywy'] ?? [])));
        if ($motywy === []) {
            $motywy = [$los->zListy(array_column($this->dane['motywy'], 'klucz'))];
        }
        $motywy = array_slice($motywy, 0, 2);

        $glowny = $this->motyw($motywy[0]);
        $ton = $this->ton((string) ($wejscie['ton'] ?? 'heroiczny'));

        $panstwo = trim((string) ($wejscie['panstwo'] ?? ''));
        $miejsce = trim((string) ($wejscie['miejsce'] ?? ''));
        $frakcja = trim((string) ($wejscie['frakcja'] ?? ''));
        $fabula = trim((string) ($wejscie['fabula'] ?? ''));

        $pola = [
            'lokacja' => $miejsce !== '' ? $miejsce : ($panstwo !== '' ? $panstwo : 'Fallathan'),
            'miejsce' => $miejsce !== '' ? $miejsce : ($panstwo !== '' ? $panstwo : 'Fallathanem'),
            'panstwo' => $panstwo,
            'frakcja' => $frakcja,
        ];

        $tytul = trim((string) ($wejscie['tytul'] ?? ''));
        if ($tytul === '') {
            $tytul = Template::render($los->zListy($glowny['tytuly']), $pola);
        }

        $zaczepka = Template::render($los->zListy($glowny['zaczepki']), $pola);
        $komplikacja = $los->zListy($this->dane['komplikacje']);
        $kulminacja = Template::render($los->zListy($this->dane['kulminacje']), $pola);
        $zakonczenia = $los->przetasuj($this->dane['zakonczenia']);

        $rodzaj = $this->wpis($this->dane['rodzaje'], (string) ($wejscie['rodzaj'] ?? 'fg'));
        $skala = $this->wpis($this->dane['skale'], (string) ($wejscie['skala'] ?? 'druzyna'));
        $dlugosc = $this->wpis($this->dane['dlugosci'], (string) ($wejscie['dlugosc'] ?? 'one_shot'));

        $etykietyMotywow = array_map(fn (string $k): string => $this->motyw($k)['etykieta'], $motywy);
        $lokalizacja = implode(', ', array_filter([$miejsce, $panstwo]));

        $L = [];
        $L[] = '# '.$tytul;
        $L[] = '';
        $L[] = 'Rodzaj: '.$rodzaj['etykieta'].'  |  Skala: '.$skala['opis'].'  |  Długość: '.$dlugosc['opis'];
        $L[] = 'Motyw: '.implode(' + ', $etykietyMotywow).'  |  Ton: '.mb_strtolower($ton['etykieta']);
        $L[] = 'Miejsce: '.($lokalizacja !== '' ? $lokalizacja : Template::render('{@lokacja w Fallathanie}', []))
            .($frakcja !== '' ? '  |  W centrum: '.$frakcja : '');
        $L[] = '';
        $L[] = '== Premisa ==';
        $L[] = $zaczepka;
        $L[] = '';
        $L[] = '== Stawka ==';
        $L[] = 'W grze jest '.$ton['stawka'].'. '
            .Template::render('{@dopisz, co konkretnie bohaterowie mogą zyskać i stracić}', []);
        $L[] = '';
        $L[] = '== Sceny ==';
        $L[] = 'I. Zawiązanie - '.$zaczepka;
        $L[] = 'II. Rozwinięcie - trop/zadanie prowadzi głębiej; pojawia się komplikacja: '.$komplikacja;
        $L[] = 'III. Kulminacja - '.$kulminacja;
        $L[] = '';
        $L[] = '== Kluczowy NPC ==';
        $L[] = $this->npc($frakcja);
        $L[] = '';
        $L[] = '== Możliwe zakończenia ==';
        foreach ($zakonczenia as $i => $zakonczenie) {
            $L[] = ($i + 1).'. '.$zakonczenie;
        }
        $L[] = '';
        $L[] = '== Powiązanie z fabułą ==';
        $L[] = $fabula !== ''
            ? 'Kontekst FG: '.$fabula
            : Template::render('{@z którą Wieścią / wydarzeniem FG sesja się łączy}', []);
        if ($rodzaj['kanoniczna']) {
            $L[] = 'Uwaga: jako Opowieść FG wymaga zgodności z kanonem i podsumowania Wieścią. '
                .Template::render('{@co z tej sesji ma trafić do Wieści}', []);
        }
        if ($frakcja !== '') {
            $L[] = 'Frakcja/rasa '.$frakcja.': '
                .Template::render('{@jak jej interesy grają w tej sesji}', []);
        }

        if ($wskazowkiMg) {
            $L[] = '';
            $L[] = '== Wskazówki dla prowadzącego ==';
            foreach ($this->dane['wskazowki_mg'] as $wskazowka) {
                $L[] = '- '.$wskazowka;
            }
            $L[] = '- '.Template::render('{@jeden sekret/atut, który możesz odsłonić, jeśli sesja przyspieszy lub zwolni}', []);
        }

        return trim((string) preg_replace("/\n{3,}/", "\n\n", implode("\n", $L)));
    }

    private function npc(string $frakcja): string
    {
        $rasaZFrakcji = $frakcja !== '' && ! preg_match('/^(Kult|Magowie)/u', $frakcja);

        return implode("\n", [
            'Miano: '.Template::render('{@imię}', []),
            'Rasa: '.($rasaZFrakcji ? $frakcja : Template::render('{@rasa}', [])),
            'Profesja / rola: '.Template::render('{@kim jest w tej sesji}', []),
            'Charakter: '.Template::render('{@alignment}', []),
            'Czego chce (jawnie): '.Template::render('{@cel oficjalny}', []),
            'Czego chce naprawdę: '.Template::render('{@ukryty cel / sekret}', []),
        ]);
    }

    /** @return array<string, mixed> */
    private function motyw(string $klucz): array
    {
        return $this->wpis($this->dane['motywy'], $klucz);
    }

    /** @return array<string, mixed> */
    private function ton(string $klucz): array
    {
        return $this->wpis($this->dane['tony'], $klucz);
    }

    /**
     * @param  array<int, array<string, mixed>> $lista
     * @return array<string, mixed>
     */
    private function wpis(array $lista, string $klucz): array
    {
        foreach ($lista as $wpis) {
            if ($wpis['klucz'] === $klucz) {
                return $wpis;
            }
        }

        throw new InvalidArgumentException("Nieznany klucz slownika: {$klucz}");
    }
}
