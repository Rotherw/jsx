<?php

declare(strict_types=1);

namespace App\Domain\Listing;

use InvalidArgumentException;

/**
 * Zamienia jeden wpis rejestru na teksty pod konkretna platforme.
 *
 * Zrodlem prawdy jest rekord produktu - eksport jest wyliczany, nigdy
 * edytowany recznie po stronie platformy (sekcja 5 systemu v2.0).
 *
 * Potrafi tez zlozyc komplet plikow do katalogu 06_THANGS_LISTING paczki
 * Commander V3 (sekcja 6), zeby wynik wpadal wprost w istniejacy workflow.
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
     * Zestaw domyslny wg sekcji 13, posortowany priorytetem.
     *
     * @return array<int, array<string, mixed>>
     */
    public function platformyDomyslne(): array
    {
        $domyslne = array_values(array_filter(
            $this->platformy,
            static fn (array $p): bool => (bool) ($p['domyslna'] ?? false),
        ));

        usort($domyslne, static fn (array $a, array $b): int => ($a['priorytet'] ?? 99) <=> ($b['priorytet'] ?? 99));

        return $domyslne;
    }

    /**
     * @param  array<string, mixed> $produkt wpis rejestru
     * @return array{platforma: string, slug: string, kod_pliku: string, jezyk: string, tytul: string, opis: string, tagi: array<int, string>, ostrzezenia: array<int, string>}
     */
    public function dlaPlatformy(array $produkt, string $slug): array
    {
        $profil = $this->profil($slug);
        $ostrzezenia = [];

        $tytul = $this->tytul($produkt, $profil, $ostrzezenia);
        $opis = $this->opis($produkt, $profil, $ostrzezenia);
        $tagi = $this->tagi((array) ($produkt['tagi'] ?? []), $profil, $ostrzezenia);

        if (($profil['limity_potwierdzone'] ?? false) === false) {
            $ostrzezenia[] = 'Limity dla tej platformy nie są potwierdzone - sprawdź formularz '
                .'podczas wystawiania i popraw je w tabeli `platformy`.';
        }

        return [
            'platforma' => (string) $profil['nazwa'],
            'slug' => (string) $profil['slug'],
            'kod_pliku' => (string) $profil['kod_pliku'],
            'jezyk' => (string) $profil['jezyk'],
            'tytul' => $tytul,
            'opis' => $opis,
            'tagi' => $tagi,
            'ostrzezenia' => $ostrzezenia,
        ];
    }

    /**
     * @param  array<string, mixed> $produkt
     * @return array<string, array<string, mixed>> klucz = slug platformy
     */
    public function wszystkie(array $produkt, bool $tylkoDomyslne = true): array
    {
        $platformy = $tylkoDomyslne ? $this->platformyDomyslne() : $this->platformy;

        $wynik = [];
        foreach ($platformy as $platforma) {
            $wynik[$platforma['slug']] = $this->dlaPlatformy($produkt, (string) $platforma['slug']);
        }

        return $wynik;
    }

    /**
     * Komplet plikow katalogu 06_THANGS_LISTING z paczki Commander V3.
     *
     * @param  array<string, mixed> $produkt
     * @return array<string, string> nazwa pliku => tresc
     */
    public function plikiPaczki(array $produkt, bool $tylkoDomyslne = true): array
    {
        $pliki = [
            'TITLE.txt' => trim((string) ($produkt['tytul_sprzedazowy'] ?? '')),
            'SHORT_DESCRIPTION.txt' => trim((string) ($produkt['krotki_opis'] ?? '')),
        ];

        foreach ($this->wszystkie($produkt, $tylkoDomyslne) as $eksport) {
            $kod = $eksport['kod_pliku'];
            $pliki["DESCRIPTION_{$kod}.txt"] = $eksport['opis'];
            $pliki["TAGS_{$kod}.txt"] = implode(', ', $eksport['tagi']);
        }

        return $pliki;
    }

    // -------------------------------------------------------------- skladniki

    /**
     * @param  array<string, mixed> $produkt
     * @param  array<string, mixed> $profil
     * @param  array<int, string>   $ostrzezenia
     */
    private function tytul(array $produkt, array $profil, array &$ostrzezenia): string
    {
        $limit = (int) $profil['limit_tytulu'];
        $pelny = trim((string) ($produkt['tytul_sprzedazowy'] ?? ''));
        $krotki = trim((string) ($produkt['tytul_krotki'] ?? ''));

        if ($pelny === '') {
            $ostrzezenia[] = 'Brak tytułu sprzedażowego w rejestrze.';

            return '';
        }

        if (mb_strlen($pelny) <= $limit) {
            return $pelny;
        }

        // Skrocony tytul platformowy jest po to, zeby nie ciac tytulu maszynowo.
        if ($krotki !== '' && mb_strlen($krotki) <= $limit) {
            return $krotki;
        }

        $ostrzezenia[] = 'Tytuł ma '.mb_strlen($pelny)."/{$limit} znaków, a skrócony tytuł "
            .($krotki === '' ? 'nie został wpisany' : 'też się nie mieści').' - przycięto maszynowo.';

        return $this->przytnij($pelny, $limit);
    }

    /**
     * @param  array<string, mixed> $produkt
     * @param  array<string, mixed> $profil
     * @param  array<int, string>   $ostrzezenia
     */
    private function opis(array $produkt, array $profil, array &$ostrzezenia): string
    {
        // CC CN ma wlasny, osobno redagowany opis (komplet metadanych, p. 10).
        if ($profil['slug'] === 'creality_cn') {
            $cn = trim((string) ($produkt['opis_cc_cn'] ?? ''));
            if ($cn === '') {
                $ostrzezenia[] = 'Brak opisu zlokalizowanego pod Creality Cloud CN - '
                    .'użyto opisu EN. To osobna pozycja kompletu metadanych.';
            } else {
                return $this->dopasujOpis($cn, $profil, $ostrzezenia);
            }
        }

        $jezyk = (string) $profil['jezyk'];
        $opis = trim((string) ($produkt['opis_'.$jezyk] ?? ''));

        if ($opis === '') {
            $opis = trim((string) ($produkt['opis_en'] ?? $produkt['opis_pl'] ?? ''));
            if ($opis === '') {
                $ostrzezenia[] = 'Brak opisu w rejestrze.';

                return '';
            }
            $ostrzezenia[] = "Brak opisu w języku „{$jezyk}” - użyto zamiennika.";
        }

        return $this->dopasujOpis($opis, $profil, $ostrzezenia);
    }

    /**
     * @param  array<string, mixed> $profil
     * @param  array<int, string>   $ostrzezenia
     */
    private function dopasujOpis(string $opis, array $profil, array &$ostrzezenia): string
    {
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

        $limit = (int) $profil['limit_opisu'];
        if ($limit > 0 && mb_strlen($opis) > $limit) {
            $ostrzezenia[] = 'Opis ma '.mb_strlen($opis)."/{$limit} znaków - przycięto.";
            $opis = $this->przytnij($opis, $limit);
        }

        return $opis;
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
                $tag = (string) preg_replace('/\s+/u', '-', mb_strtolower($tag));
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

    private function przytnij(string $tekst, int $limit): string
    {
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
