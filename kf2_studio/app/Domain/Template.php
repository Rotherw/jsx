<?php

declare(strict_types=1);

namespace App\Domain;

/**
 * Minimalny silnik szablonow uzywany przez oba generatory KF2.
 *
 *   {pole}            wartosc pola (pusty string gdy brak)
 *   {pole|tekst}      wartosc pola albo literalny tekst zapasowy
 *   {@opis}           luka do recznego wypelnienia -> [UZUPEŁNIJ: opis]
 *   [[pole? A||B]]    A gdy pole niepuste, inaczej B (spacje przy || sa znaczace)
 *   [[pole? A]]       A gdy pole niepuste, inaczej nic
 *
 * Grupy [[...]] rozwijane sa od najglebszej, wiec moga byc zagniezdzone.
 * Wewnatrz {@...} dziala podstawianie pol, ale nie kolejne {@...}.
 */
final class Template
{
    public const PLACEHOLDER_PREFIX = '[UZUPEŁNIJ: ';

    /** @param array<string, string> $pola */
    public static function render(string $szablon, array $pola): string
    {
        $tekst = self::rozwinGrupy($szablon, $pola);
        // Pola najpierw - dzieki temu {@... (np. {panstwo})} ma juz czysta tresc.
        $tekst = self::rozwinPola($tekst, $pola);

        return self::rozwinLuki($tekst);
    }

    /** Czy w tekscie zostaly nieuzupelnione luki. */
    public static function maLuki(string $tekst): bool
    {
        return str_contains($tekst, self::PLACEHOLDER_PREFIX);
    }

    /** @param array<string, string> $pola */
    private static function rozwinGrupy(string $szablon, array $pola): string
    {
        // Najglebsza grupa = taka, ktora nie zawiera w srodku "[[".
        $wzorzec = '/\[\[([a-z_]+)\?((?:(?!\[\[).)*?)\]\]/su';

        for ($i = 0; $i < 20; $i++) {
            $poprzedni = $szablon;
            $szablon = preg_replace_callback($wzorzec, static function (array $m) use ($pola): string {
                $warunek = trim($pola[$m[1]] ?? '') !== '';
                // Bez przycinania spacji - odstepy naleza do galezi, nie do separatora.
                $galezie = explode('||', $m[2], 2);

                return $warunek ? $galezie[0] : ($galezie[1] ?? '');
            }, $szablon) ?? $szablon;

            if ($szablon === $poprzedni) {
                break;
            }
        }

        return $szablon;
    }

    private static function rozwinLuki(string $tekst): string
    {
        return preg_replace_callback('/\{@([^{}]*)\}/u', static fn (array $m): string => self::luka($m[1]), $tekst) ?? $tekst;
    }

    /**
     * Podstawia w petli: pole moze siedziec w tekscie zapasowym innego pola,
     * a pojedyncze przejscie preg nie wraca do juz minietych pozycji.
     *
     * @param array<string, string> $pola
     */
    private static function rozwinPola(string $tekst, array $pola): string
    {
        for ($i = 0; $i < 10; $i++) {
            $poprzedni = $tekst;
            $tekst = self::jedenPrzebiegPol($tekst, $pola);
            if ($tekst === $poprzedni) {
                break;
            }
        }

        return $tekst;
    }

    /** @param array<string, string> $pola */
    private static function jedenPrzebiegPol(string $tekst, array $pola): string
    {
        return preg_replace_callback('/\{([a-z_]+)(?:\|([^{}]*))?\}/u', static function (array $m) use ($pola): string {
            $wartosc = trim($pola[$m[1]] ?? '');
            if ($wartosc !== '') {
                // Klamry z danych uzytkownika zaburzylyby dalsze przetwarzanie.
                return strtr($wartosc, ['{' => '(', '}' => ')']);
            }

            $zapasowy = $m[2] ?? '';

            return str_starts_with($zapasowy, '@') ? self::luka(substr($zapasowy, 1)) : $zapasowy;
        }, $tekst) ?? $tekst;
    }

    private static function luka(string $opis): string
    {
        return self::PLACEHOLDER_PREFIX.$opis.']';
    }
}
