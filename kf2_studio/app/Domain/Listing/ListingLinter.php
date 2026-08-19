<?php

declare(strict_types=1);

namespace App\Domain\Listing;

/**
 * Kontrola spojnosci listingu przed wyslaniem na platformy.
 *
 * Lapie dokladnie te rozjazdy, ktore juz sie zdarzyly na zywych listingach:
 * literowki w nazwie marki, urwane linki konczace sie na "@", listingi
 * istniejace tylko po angielsku albo tylko po polsku, powtorzone tagi.
 */
final class ListingLinter
{
    public const MARKA = 'WorkShop3D';

    /** Warianty, ktore w praktyce pojawialy sie zamiast poprawnej nazwy. */
    private const WARIANTY_MARKI = [
        'worshop3d', 'workshop 3d', 'work shop 3d', 'workshop3 d', 'wokshop3d', 'workshop3d.',
    ];

    /**
     * @param  array<string, mixed> $produkt
     * @return array<int, array{kod: string, pole: string, opis: string}>
     */
    public function sprawdz(array $produkt): array
    {
        $uwagi = [];

        $teksty = [
            'tytul_en' => (string) ($produkt['tytul_en'] ?? ''),
            'tytul_pl' => (string) ($produkt['tytul_pl'] ?? ''),
            'opis_en' => (string) ($produkt['opis_en'] ?? ''),
            'opis_pl' => (string) ($produkt['opis_pl'] ?? ''),
        ];

        foreach ($teksty as $pole => $tekst) {
            foreach ($this->bledyMarki($tekst) as $wariant) {
                $uwagi[] = [
                    'kod' => 'marka',
                    'pole' => $pole,
                    'opis' => "Nazwa marki zapisana jako \"{$wariant}\" - powinno być \"".self::MARKA.'".',
                ];
            }

            foreach ($this->urwaneLinki($tekst) as $link) {
                $uwagi[] = [
                    'kod' => 'link',
                    'pole' => $pole,
                    'opis' => "Link wygląda na urwany: \"{$link}\".",
                ];
            }
        }

        foreach ([['tytul_pl', 'tytul_en', 'tytułu'], ['opis_pl', 'opis_en', 'opisu']] as [$pl, $en, $nazwa]) {
            $maPl = trim($teksty[$pl]) !== '';
            $maEn = trim($teksty[$en]) !== '';
            if ($maPl !== $maEn) {
                $uwagi[] = [
                    'kod' => 'brak_tlumaczenia',
                    'pole' => $maPl ? $en : $pl,
                    'opis' => 'Brak '.$nazwa.' w wersji '.($maPl ? 'angielskiej' : 'polskiej').'.',
                ];
            }
        }

        $uwagi = array_merge($uwagi, $this->uwagiTagow((array) ($produkt['tagi'] ?? [])));

        return $uwagi;
    }

    /** @return array<int, string> */
    private function bledyMarki(string $tekst): array
    {
        $znalezione = [];
        $male = mb_strtolower($tekst);

        foreach (self::WARIANTY_MARKI as $wariant) {
            $pozycja = mb_strpos($male, $wariant);
            if ($pozycja === false) {
                continue;
            }

            $oryginal = mb_substr($tekst, $pozycja, mb_strlen($wariant));
            // Poprawna pisownia bywa prefiksem wariantu z kropka - nie zglaszaj jej.
            if (mb_strtolower($oryginal) === mb_strtolower(self::MARKA)) {
                continue;
            }
            $znalezione[] = $oryginal;
        }

        // Poprawna nazwa z blednym rozkladem wielkich liter.
        if (mb_strpos($male, mb_strtolower(self::MARKA)) !== false) {
            $pozycja = mb_strpos($male, mb_strtolower(self::MARKA));
            $oryginal = mb_substr($tekst, (int) $pozycja, mb_strlen(self::MARKA));
            if ($oryginal !== self::MARKA) {
                $znalezione[] = $oryginal;
            }
        }

        return array_values(array_unique($znalezione));
    }

    /**
     * Link urwany na "@" albo na samym znaku interpunkcyjnym - typowy skutek
     * kopiowania handle'a z profilu.
     *
     * @return array<int, string>
     */
    private function urwaneLinki(string $tekst): array
    {
        preg_match_all('#\bhttps?://\S*#u', $tekst, $trafienia);

        $urwane = [];
        foreach ($trafienia[0] as $link) {
            if (preg_match('#[@/\-_.]$#u', $link) || preg_match('#/@$#u', $link)) {
                $urwane[] = $link;
            }
        }

        // Samotny "@" bez uchwytu po nim.
        if (preg_match('/(^|\s)@(\s|$)/u', $tekst)) {
            $urwane[] = '@';
        }

        return array_values(array_unique($urwane));
    }

    /**
     * @param  array<int, string> $tagi
     * @return array<int, array{kod: string, pole: string, opis: string}>
     */
    private function uwagiTagow(array $tagi): array
    {
        $uwagi = [];
        $widziane = [];

        foreach ($tagi as $tag) {
            $klucz = mb_strtolower(trim((string) $tag));
            if ($klucz === '') {
                continue;
            }
            if (isset($widziane[$klucz])) {
                $uwagi[] = [
                    'kod' => 'tagi_duplikat',
                    'pole' => 'tagi',
                    'opis' => "Tag \"{$klucz}\" powtarza się.",
                ];

                continue;
            }
            $widziane[$klucz] = true;
        }

        return $uwagi;
    }
}
