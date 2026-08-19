<?php

declare(strict_types=1);

namespace App\Domain\Listing;

use InvalidArgumentException;

/**
 * Zamienia jeden wpis z centralnej bazy produktow na wersje pod konkretna
 * platforme: przycina do limitow, normalizuje tagi, usuwa to, czego dana
 * platforma nie przyjmuje.
 *
 * Zrodlem prawdy jest zawsze rekord produktu - eksport jest wyliczany,
 * nigdy edytowany recznie po stronie platformy.
 */
final class ListingExporter
{
    /** @param array<int, array<string, mixed>> $platformy */
    public function __construct(private readonly array $platformy) {}

    /** @return array<string, mixed> */
    public function profil(string $slug): array
    {
        foreach ($this->platformy as $platforma) {
            if ($platforma['slug'] === $slug) {
                return $platforma;
            }
        }

        throw new InvalidArgumentException("Nieznana platforma: {$slug}");
    }

    /**
     * @param  array<string, mixed> $produkt tytul_en, tytul_pl, opis_en, opis_pl, tagi[]
     * @return array{platforma: string, jezyk: string, tytul: string, opis: string, tagi: array<int, string>, ostrzezenia: array<int, string>}
     */
    public function dlaPlatformy(array $produkt, string $slug): array
    {
        $profil = $this->profil($slug);
        $jezyk = (string) $profil['jezyk'];
        $ostrzezenia = [];

        $tytul = trim((string) ($produkt['tytul_'.$jezyk] ?? ''));
        $opis = trim((string) ($produkt['opis_'.$jezyk] ?? ''));

        if ($tytul === '') {
            $tytul = trim((string) ($produkt['tytul_en'] ?? $produkt['tytul_pl'] ?? ''));
            $ostrzezenia[] = "Brak tytułu w języku '{$jezyk}' - użyto zamiennika.";
        }
        if ($opis === '') {
            $opis = trim((string) ($produkt['opis_en'] ?? $produkt['opis_pl'] ?? ''));
            $ostrzezenia[] = "Brak opisu w języku '{$jezyk}' - użyto zamiennika.";
        }

        if (($profil['linki_zewnetrzne'] ?? true) === false) {
            $bezLinkow = $this->usunLinki($opis);
            if ($bezLinkow !== $opis) {
                $ostrzezenia[] = 'Platforma nie przyjmuje linków zewnętrznych - usunięto je z opisu.';
                $opis = $bezLinkow;
            }
        }

        if (($profil['markdown'] ?? false) === false) {
            $opis = $this->usunMarkdown($opis);
        }

        $tytul = $this->przytnij($tytul, (int) $profil['limit_tytulu'], $ostrzezenia, 'Tytuł');
        $opis = $this->przytnij($opis, (int) $profil['limit_opisu'], $ostrzezenia, 'Opis');

        $tagi = $this->tagi((array) ($produkt['tagi'] ?? []), $profil, $ostrzezenia);

        return [
            'platforma' => $profil['nazwa'],
            'jezyk' => $jezyk,
            'tytul' => $tytul,
            'opis' => $opis,
            'tagi' => $tagi,
            'ostrzezenia' => $ostrzezenia,
        ];
    }

    /**
     * @param  array<string, mixed> $produkt
     * @return array<string, array<string, mixed>>
     */
    public function wszystkie(array $produkt): array
    {
        $wynik = [];
        foreach ($this->platformy as $platforma) {
            $wynik[$platforma['slug']] = $this->dlaPlatformy($produkt, (string) $platforma['slug']);
        }

        return $wynik;
    }

    /**
     * @param  array<int, string>   $surowe
     * @param  array<string, mixed> $profil
     * @param  array<int, string>   $ostrzezenia
     * @return array<int, string>
     */
    private function tagi(array $surowe, array $profil, array &$ostrzezenia): array
    {
        $tagi = [];
        foreach ($surowe as $tag) {
            $tag = trim((string) $tag);
            if ($tag === '') {
                continue;
            }

            if (($profil['format_tagu'] ?? 'swobodny') === 'lowercase') {
                $tag = mb_strtolower($tag);
                $tag = (string) preg_replace('/\s+/u', '-', $tag);
            }

            if (! in_array($tag, $tagi, true)) {
                $tagi[] = $tag;
            }
        }

        $limit = (int) $profil['limit_tagow'];
        if (count($tagi) > $limit) {
            $ostrzezenia[] = 'Za dużo tagów ('.count($tagi)."/{$limit}) - obcięto nadmiar.";
            $tagi = array_slice($tagi, 0, $limit);
        }

        return $tagi;
    }

    /** @param array<int, string> $ostrzezenia */
    private function przytnij(string $tekst, int $limit, array &$ostrzezenia, string $co): string
    {
        if ($limit <= 0 || mb_strlen($tekst) <= $limit) {
            return $tekst;
        }

        $ostrzezenia[] = "{$co} przekracza limit ".mb_strlen($tekst)."/{$limit} znaków - przycięto.";

        return rtrim(mb_substr($tekst, 0, $limit - 1)).'…';
    }

    private function usunLinki(string $tekst): string
    {
        $tekst = (string) preg_replace('#\bhttps?://\S+#u', '', $tekst);

        return trim((string) preg_replace("/[ \t]{2,}/", ' ', $tekst));
    }

    private function usunMarkdown(string $tekst): string
    {
        $tekst = (string) preg_replace('/\[([^\]]+)\]\([^)]+\)/u', '$1', $tekst);
        $tekst = (string) preg_replace('/(\*\*|__|\*|_|`)/u', '', $tekst);
        $tekst = (string) preg_replace('/^#{1,6}\s*/mu', '', $tekst);

        return trim($tekst);
    }
}
