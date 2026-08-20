<?php

declare(strict_types=1);

namespace App\Domain\Listing;

/**
 * Kontrola wpisu w rejestrze przed publikacja.
 *
 * Reguly pochodza wprost z "WorkShop3D x KF2 - System Operacyjny v2.0":
 *   sekcja 8  - nazewnictwo,
 *   sekcja 10 - zelazne reguly faktow i lore,
 *   sekcja 11 - licencje,
 *   sekcja 13 - priorytet i zasady platform,
 *   sekcja 14 - kontrola przed publikacja.
 *
 * Kazda uwaga ma wage:
 *   'blokuje' - nie wystawiamy, dopoki nie poprawione,
 *   'uwaga'   - warto poprawic, ale nie zatrzymuje wydania.
 */
final class ListingLinter
{
    public const MARKA = 'WorkShop3D';

    /** Wzorzec tytulu KF2: "KF2 [Model Name] - [Search Descriptor] - WorkShop3D". */
    private const WZORZEC_TYTULU_KF2 = '/^KF2\s+.+\s+-\s+.+\s+-\s+WorkShop3D$/u';

    /** Warianty, ktore w praktyce pojawialy sie zamiast poprawnej nazwy marki. */
    private const WARIANTY_MARKI = [
        'worshop3d', 'workshop 3d', 'work shop 3d', 'workshop3 d', 'wokshop3d',
    ];

    /** Deklaracje, ktorych nie wolno stawiac bez potwierdzenia (sekcja 10). */
    private const DEKLARACJE_DRUKU = [
        'supportless' => 'wymaga_podpor',
        'support-free' => 'wymaga_podpor',
        'no supports' => 'wymaga_podpor',
        'bez podpor' => 'wymaga_podpor',
        'print tested' => 'stan_testu',
        'print-tested' => 'stan_testu',
        'tested print' => 'stan_testu',
        'przetestowany wydruk' => 'stan_testu',
    ];

    /** Statusy, przy ktorych oferta musi juz miec dzialajacy link (sekcja 13). */
    private const STATUSY_OPUBLIKOWANE = ['PUBLISHED', 'UPLOADED'];

    /**
     * @param  array<string, mixed> $produkt wpis rejestru
     * @return array<int, array{kod: string, pole: string, waga: string, opis: string}>
     */
    public function sprawdz(array $produkt): array
    {
        return array_merge(
            $this->uwagiMarki($produkt),
            $this->uwagiTytulu($produkt),
            $this->uwagiKolekcji($produkt),
            $this->uwagiLinkow($produkt),
            $this->uwagiTlumaczen($produkt),
            $this->uwagiTagow((array) ($produkt['tagi'] ?? [])),
            $this->uwagiLore($produkt),
            $this->uwagiDeklaracjiDruku($produkt),
            $this->uwagiLicencji($produkt),
            $this->uwagiPublikacji($produkt),
        );
    }

    /** Czy cokolwiek blokuje wystawienie. */
    public function blokuje(array $uwagi): bool
    {
        foreach ($uwagi as $uwaga) {
            if ($uwaga['waga'] === 'blokuje') {
                return true;
            }
        }

        return false;
    }

    /**
     * Nazwa pliku wg sekcji 8: angielski, ASCII, podkreslniki zamiast spacji,
     * bez "final_final2".
     *
     * @return array<int, string> lista problemow; pusta gdy nazwa jest poprawna
     */
    public function sprawdzNazwePliku(string $nazwa): array
    {
        $problemy = [];

        if (preg_match('/[^\x20-\x7E]/', $nazwa)) {
            $problemy[] = 'zawiera znaki spoza ASCII (m.in. polskie znaki)';
        }
        if (str_contains($nazwa, ' ')) {
            $problemy[] = 'zawiera spacje - uzyj podkreslnikow';
        }
        if (preg_match('/final[_\-]?final|final\d|_ost(ateczny)?\d*\./iu', $nazwa)) {
            $problemy[] = 'nazwa typu "final_final2" - uzyj wersjonowania v1 / v1_1 / print_ready';
        }

        return $problemy;
    }

    // ---------------------------------------------------------------- reguly

    /** @return array<int, array<string, string>> */
    private function uwagiMarki(array $produkt): array
    {
        $uwagi = [];

        foreach ($this->teksty($produkt) as $pole => $tekst) {
            // Pisownia marki dotyczy prozy, nie domen: "workshop3d.example"
            // w adresie to nie literowka, wiec adresy wycinamy z kontroli.
            $tekst = $this->bezAdresow($tekst);
            $male = mb_strtolower($tekst);

            foreach (self::WARIANTY_MARKI as $wariant) {
                if (mb_strpos($male, $wariant) !== false) {
                    $pozycja = (int) mb_strpos($male, $wariant);
                    $oryginal = mb_substr($tekst, $pozycja, mb_strlen($wariant));
                    $uwagi[] = $this->uwaga('marka', $pole, 'blokuje',
                        "Nazwa marki zapisana jako \"{$oryginal}\" - powinno być \"".self::MARKA.'".');
                }
            }

            // Poprawna nazwa, ale zly rozklad wielkich liter.
            $pozycja = mb_strpos($male, mb_strtolower(self::MARKA));
            if ($pozycja !== false) {
                $oryginal = mb_substr($tekst, $pozycja, mb_strlen(self::MARKA));
                if ($oryginal !== self::MARKA) {
                    $uwagi[] = $this->uwaga('marka', $pole, 'blokuje',
                        "Marka zapisana jako \"{$oryginal}\" - obowiązuje dokładnie \"".self::MARKA.'".');
                }
            }
        }

        return $this->odduplikuj($uwagi);
    }

    /** @return array<int, array<string, string>> */
    private function uwagiTytulu(array $produkt): array
    {
        $tytul = trim((string) ($produkt['tytul_sprzedazowy'] ?? ''));
        $kf2 = ($produkt['swiat'] ?? 'kf2') === 'kf2';
        $uwagi = [];

        if ($tytul === '') {
            return [$this->uwaga('tytul_brak', 'tytul_sprzedazowy', 'blokuje',
                'Brak tytułu sprzedażowego.')];
        }

        if ($kf2 && ! preg_match(self::WZORZEC_TYTULU_KF2, $tytul)) {
            $uwagi[] = $this->uwaga('tytul_wzorzec', 'tytul_sprzedazowy', 'uwaga',
                'Tytuł nie pasuje do wzorca "KF2 [Model Name] - [Search Descriptor] - WorkShop3D".');
        }

        // Prefiks KF2 zarezerwowany dla produktow KF2 (sekcja 8).
        if (! $kf2 && preg_match('/(^|\s)KF2(\s|$)/u', $tytul)) {
            $uwagi[] = $this->uwaga('kf2_poza_kf2', 'tytul_sprzedazowy', 'blokuje',
                'Produkt nie jest oznaczony jako KF2, a tytuł używa prefiksu "KF2".');
        }

        if (stripos($tytul, 'chibi') !== false) {
            $uwagi[] = $this->uwaga('chibi', 'tytul_sprzedazowy', 'uwaga',
                'Słowo "Chibi" w tytule sprzedażowym - dopuszczalne tylko na wyraźne życzenie.');
        }

        return $uwagi;
    }

    /** @return array<int, array<string, string>> */
    private function uwagiKolekcji(array $produkt): array
    {
        $kolekcja = trim((string) ($produkt['kolekcja'] ?? ''));
        $naleziDoKufla = mb_stripos($kolekcja, 'Kufel i Kości') !== false
            || mb_stripos($kolekcja, 'Kufel i Kosci') !== false;

        if ($naleziDoKufla) {
            return [];
        }

        foreach ($this->teksty($produkt) as $pole => $tekst) {
            if (mb_stripos($tekst, 'Kufel i Ko') !== false) {
                return [$this->uwaga('kufel_i_kosci', $pole, 'blokuje',
                    'Nazwa kolekcji „Kufel i Kości” użyta przy produkcie, który do niej nie należy.')];
            }
        }

        return [];
    }

    /** @return array<int, array<string, string>> */
    private function uwagiLinkow(array $produkt): array
    {
        $uwagi = [];

        foreach ($this->teksty($produkt) as $pole => $tekst) {
            preg_match_all('#\bhttps?://\S*#u', $tekst, $trafienia);

            foreach (array_unique($trafienia[0]) as $link) {
                if (preg_match('#[@/\-_.]$#u', $link)) {
                    $uwagi[] = $this->uwaga('link', $pole, 'blokuje',
                        "Link wygląda na urwany: \"{$link}\".");
                }
            }

            if (preg_match('/(^|\s)@(\s|$)/u', $tekst)) {
                $uwagi[] = $this->uwaga('link', $pole, 'blokuje',
                    'Samotny znak "@" bez uchwytu - prawdopodobnie urwany link do profilu.');
            }
        }

        return $uwagi;
    }

    /** @return array<int, array<string, string>> */
    private function uwagiTlumaczen(array $produkt): array
    {
        $uwagi = [];

        $pary = [
            ['nazwa_pl', 'nazwa_en', 'nazwy kanonicznej'],
            ['opis_pl', 'opis_en', 'opisu'],
        ];

        foreach ($pary as [$pl, $en, $czego]) {
            $maPl = trim((string) ($produkt[$pl] ?? '')) !== '';
            $maEn = trim((string) ($produkt[$en] ?? '')) !== '';

            if ($maPl !== $maEn) {
                $uwagi[] = $this->uwaga('brak_tlumaczenia', $maPl ? $en : $pl, 'uwaga',
                    'Brak '.$czego.' w wersji '.($maPl ? 'angielskiej' : 'polskiej').'.');
            }
        }

        return $uwagi;
    }

    /**
     * @param  array<int, string> $tagi
     * @return array<int, array<string, string>>
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
                $uwagi[] = $this->uwaga('tagi_duplikat', 'tagi', 'uwaga',
                    "Tag \"{$klucz}\" powtarza się.");

                continue;
            }
            $widziane[$klucz] = true;
        }

        return $uwagi;
    }

    /** Sekcja 10: do wpisu zawsze dołączamy link albo informację o źródle. */
    private function uwagiLore(array $produkt): array
    {
        if (($produkt['swiat'] ?? 'kf2') !== 'kf2') {
            return [];
        }

        $maZrodlo = trim((string) ($produkt['zrodlo_lore'] ?? '')) !== ''
            || trim((string) ($produkt['link_lore'] ?? '')) !== '';

        if ($maZrodlo) {
            return [];
        }

        return [$this->uwaga('lore_bez_zrodla', 'link_lore', 'blokuje',
            'Produkt KF2 bez źródła lore. Lore pochodzi wyłącznie z wiki.kf2.pl '
            .'albo materiału potwierdzonego przez właściciela świata.')];
    }

    /** Sekcja 10: nie deklarujemy tego, czego nie sprawdzono. */
    private function uwagiDeklaracjiDruku(array $produkt): array
    {
        $uwagi = [];

        foreach ($this->teksty($produkt) as $pole => $tekst) {
            $male = mb_strtolower($tekst);

            foreach (self::DEKLARACJE_DRUKU as $fraza => $poleDowodu) {
                if (! str_contains($male, $fraza)) {
                    continue;
                }

                $potwierdzone = $poleDowodu === 'wymaga_podpor'
                    ? array_key_exists('wymaga_podpor', $produkt) && $produkt['wymaga_podpor'] !== null
                    : trim((string) ($produkt[$poleDowodu] ?? '')) !== '';

                if (! $potwierdzone) {
                    $uwagi[] = $this->uwaga('niepotwierdzona_deklaracja', $pole, 'blokuje',
                        "Opis deklaruje „{$fraza}”, a pole „{$poleDowodu}” w rejestrze jest puste. "
                        .'Nie deklarujemy tego, czego nie sprawdzono.');
                }
            }
        }

        return $this->odduplikuj($uwagi);
    }

    /** Sekcja 11: jedna podstawowa licencja obowiązująca wszędzie. */
    private function uwagiLicencji(array $produkt): array
    {
        $uwagi = [];

        if (trim((string) ($produkt['licencja_podstawowa'] ?? '')) === '') {
            $uwagi[] = $this->uwaga('brak_licencji', 'licencja_podstawowa', 'blokuje',
                'Brak licencji podstawowej. Każdy produkt ma jedną, obowiązującą na wszystkich platformach.');
        }

        $maKomercyjna = trim((string) ($produkt['licencja_komercyjna'] ?? '')) !== '';
        $limit = trim((string) ($produkt['limit_sprzedazy'] ?? ''));

        if ($maKomercyjna && $limit === '') {
            $uwagi[] = $this->uwaga('limit_sprzedazy', 'limit_sprzedazy', 'uwaga',
                'Licencja komercyjna bez wpisanego limitu sprzedaży - sekcja 11 każe wpisywać go wprost.');
        }

        return $uwagi;
    }

    /** Sekcja 13: publikację uznajemy za wykonaną dopiero po działającym linku. */
    private function uwagiPublikacji(array $produkt): array
    {
        $status = strtoupper(trim((string) ($produkt['status'] ?? '')));

        if (! in_array($status, self::STATUSY_OPUBLIKOWANE, true)) {
            return [];
        }

        if (trim((string) ($produkt['link'] ?? '')) === '') {
            return [$this->uwaga('publikacja_bez_linku', 'link', 'blokuje',
                "Status „{$status}” bez zapisanego linku do oferty.")];
        }

        return [];
    }

    // -------------------------------------------------------------- pomocnicze

    /** @return array<string, string> pola tekstowe podlegające kontroli */
    private function teksty(array $produkt): array
    {
        $pola = [
            'nazwa_pl', 'nazwa_en', 'tytul_sprzedazowy', 'krotki_opis',
            'opis_pl', 'opis_en', 'opis_cc_cn', 'tytul_posta', 'cta',
        ];

        $teksty = [];
        foreach ($pola as $pole) {
            $wartosc = trim((string) ($produkt[$pole] ?? ''));
            if ($wartosc !== '') {
                $teksty[$pole] = $wartosc;
            }
        }

        return $teksty;
    }

    /** Usuwa adresy URL i domeny, zeby nie mieszaly sie do kontroli pisowni. */
    private function bezAdresow(string $tekst): string
    {
        $tekst = (string) preg_replace('#\bhttps?://\S+#u', ' ', $tekst);

        return (string) preg_replace('#\b[\w.-]+\.(?:com|pl|net|org|io|eu|cn|example)\b\S*#ui', ' ', $tekst);
    }

    /** @return array<string, string> */
    private function uwaga(string $kod, string $pole, string $waga, string $opis): array
    {
        return ['kod' => $kod, 'pole' => $pole, 'waga' => $waga, 'opis' => $opis];
    }

    /**
     * @param  array<int, array<string, string>> $uwagi
     * @return array<int, array<string, string>>
     */
    private function odduplikuj(array $uwagi): array
    {
        $widziane = [];
        $wynik = [];

        foreach ($uwagi as $uwaga) {
            $klucz = $uwaga['kod'].'|'.$uwaga['pole'].'|'.$uwaga['opis'];
            if (isset($widziane[$klucz])) {
                continue;
            }
            $widziane[$klucz] = true;
            $wynik[] = $uwaga;
        }

        return $wynik;
    }
}
