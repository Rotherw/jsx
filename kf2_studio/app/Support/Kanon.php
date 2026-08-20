<?php

declare(strict_types=1);

namespace App\Support;

use App\Models\KanonFakt;
use App\Models\KanonWpis;
use App\Models\Platforma;
use App\Models\SesjaMotyw;
use App\Models\SesjaSlownik;
use App\Models\SesjaTekst;
use App\Models\WikiTyp;
use Throwable;

/**
 * Czyta dane domenowe z bazy i podaje je generatorom w tym samym ksztalcie,
 * co pliki w database/data.
 *
 * Gdy baza jest jeszcze pusta albo niedostepna (swiezy klon, migracje przed
 * uruchomieniem), spada na pliki - aplikacja startuje zamiast wybuchac.
 */
final class Kanon
{
    /** @var array<string, mixed> */
    private array $cache = [];

    /** @return array<int, array<string, mixed>> */
    public function typyWiki(): array
    {
        return $this->pamietaj('wiki_typy', function (): array {
            $typy = WikiTyp::orderBy('kolejnosc')->get()
                ->map(static fn (WikiTyp $typ): array => [
                    'klucz' => $typ->klucz,
                    'etykieta' => $typ->etykieta,
                    'pola' => $typ->pola,
                    'lead' => $typ->lead,
                    'sekcje' => $typ->sekcje,
                ])->all();

            return $typy !== [] ? $typy : $this->zPliku('wiki_types');
        }, fn (): array => $this->zPliku('wiki_types'));
    }

    /** @return array<string, mixed> */
    public function slownikSesji(): array
    {
        return $this->pamietaj('sesje', function (): array {
            $motywy = SesjaMotyw::orderBy('kolejnosc')->get()
                ->map(static fn (SesjaMotyw $m): array => [
                    'klucz' => $m->klucz,
                    'etykieta' => $m->etykieta,
                    'tytuly' => $m->tytuly,
                    'zaczepki' => $m->zaczepki,
                ])->all();

            if ($motywy === []) {
                return $this->zPliku('session_data');
            }

            $slownik = static fn (string $rodzaj): array => SesjaSlownik::where('rodzaj', $rodzaj)
                ->orderBy('kolejnosc')->get()
                ->map(static fn (SesjaSlownik $s): array => array_merge(
                    ['klucz' => $s->klucz, 'etykieta' => $s->etykieta],
                    $s->atrybuty ?? [],
                ))->all();

            $teksty = static fn (string $rodzaj): array => SesjaTekst::where('rodzaj', $rodzaj)
                ->orderBy('kolejnosc')->pluck('tresc')->all();

            return [
                'motywy' => $motywy,
                'tony' => $slownik('ton'),
                'rodzaje' => $slownik('rodzaj'),
                'skale' => $slownik('skala'),
                'dlugosci' => $slownik('dlugosc'),
                'komplikacje' => $teksty('komplikacja'),
                'kulminacje' => $teksty('kulminacja'),
                'zakonczenia' => $teksty('zakonczenie'),
                'wskazowki_mg' => $teksty('wskazowka_mg'),
            ];
        }, fn (): array => $this->zPliku('session_data'));
    }

    /** @return array<int, array<string, mixed>> */
    public function platformy(): array
    {
        return $this->pamietaj('platformy', function (): array {
            $platformy = Platforma::orderBy('kolejnosc')->get()
                ->map(static fn (Platforma $p): array => [
                    'slug' => $p->slug,
                    'nazwa' => $p->nazwa,
                    'jezyk' => $p->jezyk,
                    'limit_tytulu' => $p->limit_tytulu,
                    'limit_opisu' => $p->limit_opisu,
                    'limit_tagow' => $p->limit_tagow,
                    'format_tagu' => $p->format_tagu,
                    'markdown' => $p->markdown,
                    'linki_zewnetrzne' => $p->linki_zewnetrzne,
                    'uwagi' => $p->uwagi,
                ])->all();

            return $platformy !== [] ? $platformy : $this->zPliku('platforms');
        }, fn (): array => $this->zPliku('platforms'));
    }

    /** Fakty pokazywane w zakladce "Kanon". @return array<int, array<string, string>> */
    public function fakty(): array
    {
        $zPliku = fn (): array => array_map(
            static fn (array $f): array => ['etykieta' => $f['etykieta'], 'wartosc' => $f['wartosc']],
            $this->zPliku('canon')['facts'],
        );

        return $this->pamietaj('fakty', function () use ($zPliku): array {
            $fakty = KanonFakt::orderBy('kolejnosc')->get()
                ->map(static fn (KanonFakt $f): array => [
                    'etykieta' => $f->etykieta, 'wartosc' => $f->wartosc,
                ])->all();

            return $fakty !== [] ? $fakty : $zPliku();
        }, $zPliku);
    }

    /** Lista wyboru dla formularzy. @return array<int, string> */
    public function lista(string $kategoria): array
    {
        return $this->pamietaj('lista.'.$kategoria, function () use ($kategoria): array {
            $wartosci = KanonWpis::where('kategoria', $kategoria)
                ->orderBy('kolejnosc')->pluck('wartosc')->all();

            return $wartosci !== [] ? $wartosci : $this->listaZPliku($kategoria);
        }, fn (): array => $this->listaZPliku($kategoria));
    }

    /** @return array<int, string> */
    private function listaZPliku(string $kategoria): array
    {
        $canon = $this->zPliku('canon');

        return match ($kategoria) {
            'kontynent' => $canon['kontynenty'],
            'panstwo' => $canon['panstwa'],
            'ksiestwo' => $canon['ksiestwa_imperium'],
            'rasa' => $canon['rasy'],
            'frakcja' => array_merge($canon['rasy'], $canon['frakcje_dodatkowe']),
            'lokacja' => $canon['lokacje'],
            'charakter' => $canon['charaktery'],
            default => [],
        };
    }

    /** @return array<mixed> */
    private function zPliku(string $nazwa): array
    {
        return require database_path("data/{$nazwa}.php");
    }

    /**
     * @param  callable(): array<mixed> $zBazy
     * @param  callable(): array<mixed> $awaryjnie
     * @return array<mixed>
     */
    private function pamietaj(string $klucz, callable $zBazy, callable $awaryjnie): array
    {
        if (! array_key_exists($klucz, $this->cache)) {
            try {
                $this->cache[$klucz] = $zBazy();
            } catch (Throwable) {
                // Brak tabel / brak polaczenia - jedziemy na plikach.
                $this->cache[$klucz] = $awaryjnie();
            }
        }

        return $this->cache[$klucz];
    }
}
