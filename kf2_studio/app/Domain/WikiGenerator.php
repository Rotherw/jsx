<?php

declare(strict_types=1);

namespace App\Domain;

use InvalidArgumentException;

/**
 * Generator artykulow Wiki Fallathanu.
 *
 * Zasada zero-wymyslania: generator nie tworzy faktow. Czego uzytkownik
 * nie poda, zostaje oznaczone jako [UZUPEŁNIJ: ...] - dzieki temu kanon
 * Thorana nie rozjezdza sie z wiki.
 */
final class WikiGenerator
{
    public const FORMAT_WIKI = 'wiki';
    public const FORMAT_TEKST = 'tekst';

    public const STOPKA = 'Świat KF2 - Kroniki Fallathanu (Thoran).';

    /** @param array<int, array<string, mixed>> $typy zawartosc database/data/wiki_types.php */
    public function __construct(private readonly array $typy) {}

    /** @return array<int, array<string, mixed>> */
    public function typy(): array
    {
        return $this->typy;
    }

    /** @return array<string, mixed> */
    public function typ(string $klucz): array
    {
        foreach ($this->typy as $typ) {
            if ($typ['klucz'] === $klucz) {
                return $typ;
            }
        }

        throw new InvalidArgumentException("Nieznany typ artykulu: {$klucz}");
    }

    /**
     * @param array<string, string> $dane nazwa, kontynent, panstwo, rasa, rola,
     *                                    charakter, rok, zarys
     */
    public function generuj(
        string $typKlucz,
        array $dane,
        string $ton = 'domyslny',
        string $format = self::FORMAT_WIKI,
        bool $zeStopka = false,
    ): string {
        $typ = $this->typ($typKlucz);
        $pola = $this->przygotujPola($typ, $dane);

        $linie = [];
        $nazwa = $pola['nazwa'] !== ''
            ? $pola['nazwa']
            : Template::render('{nazwa|@nazwa}', $pola);

        $linie[] = $format === self::FORMAT_WIKI ? "= {$nazwa} =" : mb_strtoupper($nazwa);
        $linie[] = '';
        $linie[] = Template::render($this->lead($typ, $ton), $pola);
        $linie[] = '';

        foreach ($typ['sekcje'] as [$naglowek, $szablon]) {
            $linie[] = $format === self::FORMAT_WIKI ? "== {$naglowek} ==" : "{$naglowek}:";
            $linie[] = Template::render($szablon, $pola);
            $linie[] = '';
        }

        if ($zeStopka) {
            $linie[] = $format === self::FORMAT_WIKI ? '----' : '---';
            $linie[] = self::STOPKA;
        }

        return $this->sklej($linie);
    }

    /**
     * Pola sa filtrowane wg widocznosci danego typu - ukryty widget nie moze
     * przeciekac do tresci artykulu, nawet jesli formularz cos przyslal.
     *
     * @param  array<string, mixed>  $typ
     * @param  array<string, string> $dane
     * @return array<string, string>
     */
    private function przygotujPola(array $typ, array $dane): array
    {
        $widoczne = $typ['pola'];
        $we = static fn (string $klucz): bool => in_array($klucz, $widoczne, true);
        $daj = static fn (string $klucz): string => trim((string) ($dane[$klucz] ?? ''));

        $pola = [
            'nazwa' => $daj('nazwa'),
            'zarys' => $daj('zarys'),
            'kontynent' => $we('kontynent') ? $daj('kontynent') : '',
            'panstwo' => $we('panstwo') ? $daj('panstwo') : '',
            'rasa' => $we('rasa') ? $daj('rasa') : '',
            'rola' => $we('rola') ? $daj('rola') : '',
            'charakter' => $we('charakter') ? $daj('charakter') : '',
            'rok' => $we('rok') ? $daj('rok') : '',
        ];

        // "poza panstwami" i "wlasny kontynent" to wybory UI, nie nazwy wlasne.
        if ($pola['panstwo'] === 'ziemie_niczyje') {
            $pola['panstwo'] = '';
        }
        if ($pola['kontynent'] === 'wlasny') {
            $pola['kontynent'] = '';
        }

        $pola['gdzie'] = implode(', ', array_filter([$pola['panstwo'], $pola['kontynent']]));

        return $pola;
    }

    /** @param array<string, mixed> $typ */
    private function lead(array $typ, string $ton): string
    {
        return $typ['lead'][$ton] ?? $typ['lead']['domyslny'];
    }

    /** @param array<int, string> $linie */
    private function sklej(array $linie): string
    {
        return trim((string) preg_replace("/\n{3,}/", "\n\n", implode("\n", $linie)));
    }
}
