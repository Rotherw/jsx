<?php

declare(strict_types=1);

namespace App\Domain;

use Random\Engine\Mt19937;
use Random\Randomizer;

/**
 * Deterministyczny losownik z wlasnym stanem - nie dotyka globalnego mt_rand,
 * wiec dwa generatory dzialajace obok siebie nie mieszaja sobie wynikow.
 *
 * To samo ziarno zawsze daje te sama sekwencje, na tej samej wersji PHP.
 */
final class Losowanie
{
    private readonly Randomizer $randomizer;

    public function __construct(int $ziarno)
    {
        $this->randomizer = new Randomizer(new Mt19937($ziarno));
    }

    /**
     * @template T
     * @param  array<int, T> $lista
     * @return T
     */
    public function zListy(array $lista)
    {
        $lista = array_values($lista);

        return $lista[$this->randomizer->getInt(0, count($lista) - 1)];
    }

    /**
     * @param  array<int, mixed> $lista
     * @return array<int, mixed>
     */
    public function przetasuj(array $lista): array
    {
        return $this->randomizer->shuffleArray(array_values($lista));
    }
}
