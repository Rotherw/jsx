<?php

/**
 * Dane generatora sesji (Opowiesci Fallathanu).
 * Zrodlo: KF2-Generator-Sesji.html.
 *
 * W zaczepkach, kulminacjach i tytulach dziala ta sama skladnia szablonu
 * co w wiki (App\Domain\Template). Uzywane pola: {miejsce}, {lokacja}.
 */
return [
    'tony' => [
        ['klucz' => 'heroiczny',  'etykieta' => 'Heroiczny',  'stawka' => 'ocalenie kogoś/czegoś ważnego i honor bohaterów'],
        ['klucz' => 'mroczny',    'etykieta' => 'Mroczny',    'stawka' => 'przetrwanie i to, ile człowieczeństwa zostanie po drodze'],
        ['klucz' => 'polityczny', 'etykieta' => 'Polityczny', 'stawka' => 'układ sił, wpływy i przyszłe sojusze'],
        ['klucz' => 'przygodowy', 'etykieta' => 'Przygodowy', 'stawka' => 'nagroda, sława i to, co czeka za horyzontem'],
    ],

    'rodzaje' => [
        ['klucz' => 'fg',        'etykieta' => 'Fabuła Główna (kanon → Wieść)', 'kanoniczna' => true],
        ['klucz' => 'prywatna',  'etykieta' => 'Prywatna (niekanoniczna)',      'kanoniczna' => false],
    ],

    'skale' => [
        ['klucz' => 'kameralna', 'etykieta' => 'Kameralna (1-2 postacie)', 'opis' => 'kameralna (1-2)'],
        ['klucz' => 'druzyna',   'etykieta' => 'Drużyna (3-5)',           'opis' => 'drużyna (3-5)'],
        ['klucz' => 'wielka',    'etykieta' => 'Wielka (wątek globalny)', 'opis' => 'wielka (wątek globalny)'],
    ],

    'dlugosci' => [
        ['klucz' => 'one_shot', 'etykieta' => 'One-shot',        'opis' => 'one-shot'],
        ['klucz' => 'multi',    'etykieta' => 'Wieloczęściowa',  'opis' => 'wieloczęściowa'],
    ],

    'motywy' => [
        [
            'klucz' => 'intryga',
            'etykieta' => 'Intryga',
            'tytuly' => ['Cienie nad {miejsce}', 'Gra masek', 'Szept za tronem', 'Dług krwi'],
            'zaczepki' => [
                'Do {lokacja} dociera wieść, która po cichu przewraca układ sił; ktoś chce, by bohaterowie wmieszali się po właściwej stronie.',
                'Wpływowa osoba w {lokacja} prosi bohaterów o usługę, której nie chce nazwać wprost - i płaci zbyt hojnie.',
            ],
        ],
        [
            'klucz' => 'sledztwo',
            'etykieta' => 'Śledztwo',
            'tytuly' => ['Milczenie {miejsce}', 'Ślad, którego nie ma', 'Co skrywa {miejsce}', 'Pytanie bez odpowiedzi'],
            'zaczepki' => [
                'W {lokacja} dochodzi do czegoś, czego nikt nie potrafi (lub nie chce) wyjaśnić; bohaterowie są pierwszymi, którzy zaczynają pytać.',
                'Coś lub ktoś znika w {lokacja}, a poszlaki celowo prowadzą w złą stronę.',
            ],
        ],
        [
            'klucz' => 'bitwa',
            'etykieta' => 'Bitwa / Potyczka',
            'tytuly' => ['Mury {miejsce}', 'Ostatni szaniec', 'Kiedy padnie {miejsce}', 'Żelazo i ogień'],
            'zaczepki' => [
                'Nad {lokacja} zbiera się burza - zbrojny konflikt wisi na włosku, a bohaterowie stają po środku.',
                'Obrona {lokacja} zależy od garstki, do której należeć będą bohaterowie.',
            ],
        ],
        [
            'klucz' => 'wyprawa',
            'etykieta' => 'Wyprawa',
            'tytuly' => ['Droga do {miejsce}', 'Za granicą map', 'Szlak Wygnańców', 'Ku nieznanemu'],
            'zaczepki' => [
                'Z {lokacja} wyrusza wyprawa w miejsce, z którego rzadko się wraca; bohaterów zwerbowano nie bez powodu.',
                'Cel leży daleko za {lokacja}, a droga jest równie groźna jak to, co czeka na końcu.',
            ],
        ],
        [
            'klucz' => 'dyplomacja',
            'etykieta' => 'Dyplomacja',
            'tytuly' => ['Poselstwo do {miejsce}', 'Cena pokoju', 'Słowo i pieczęć', 'Krucha równowaga'],
            'zaczepki' => [
                'Do {lokacja} przybywa poselstwo z propozycją, która dzieli zebranych; jedno słowo może przeważyć szalę.',
                'W {lokacja} ma dojść do rozmów, których obie strony boją się bardziej niż wojny.',
            ],
        ],
        [
            'klucz' => 'groza',
            'etykieta' => 'Groza',
            'tytuly' => ['Noc nad {miejsce}', 'To, co czeka w ciemności', 'Klątwa {miejsce}', 'Zimny oddech'],
            'zaczepki' => [
                'W {lokacja} dzieje się coś, czego mieszkańcy nie chcą nazywać po imieniu - a noce robią się coraz dłuższe.',
                'To, co przyszło do {lokacja}, nie powinno istnieć; bohaterowie poznają to jako pierwsi.',
            ],
        ],
        [
            'klucz' => 'mistyka',
            'etykieta' => 'Mistyka / Magia',
            'tytuly' => ['Echo WDM', 'Pęknięty kryształ', 'Znak na niebie', 'Tam, gdzie cienka jest zasłona'],
            'zaczepki' => [
                'Echo dawnej WDM daje o sobie znać w {lokacja} w sposób, którego nikt się nie spodziewał.',
                'W {lokacja} pojawia się znak, który magowie odczytują jako ostrzeżenie - lub zaproszenie.',
            ],
        ],
        [
            'klucz' => 'ratunek',
            'etykieta' => 'Ratunek',
            'tytuly' => ['Wyrwać z {miejsce}', 'Nim zapadnie noc', 'Dług wdzięczności', 'Ostatnia szansa'],
            'zaczepki' => [
                'Ktoś ważny utknął w {lokacja}, a czas działa na niekorzyść; ratunek spada na bohaterów.',
                'W {lokacja} trzeba wyrwać kogoś z rąk, które nie wypuszczają łatwo.',
            ],
        ],
        [
            'klucz' => 'polowanie',
            'etykieta' => 'Polowanie',
            'tytuly' => ['Bestia z {miejsce}', 'Tropem', 'Łowy', 'Coś poluje pierwsze'],
            'zaczepki' => [
                'Coś poluje w okolicy {lokacja}, a kolejne ofiary nie pozostawiają wątpliwości, że to nie zwykła bestia.',
                'Na bohaterów spada zadanie, by w {lokacja} schwytać lub uziemić to, czego inni się boją.',
            ],
        ],
        [
            'klucz' => 'handel',
            'etykieta' => 'Handel',
            'tytuly' => ['Kontrakt z {miejsce}', 'Za garść Krabów', 'Towar przeklęty', 'Bilans strat'],
            'zaczepki' => [
                'W {lokacja} dobija się intratny, lecz podejrzany kontrakt; za garść Krabów kryje się więcej, niż widać.',
                'Karawana/towar w {lokacja} okazuje się czymś więcej niż zwykłym ładunkiem.',
            ],
        ],
    ],

    'komplikacje' => [
        'Sojusznik bohaterów ma własny, ukryty cel - i właśnie zaczyna go realizować.',
        'To, czego szukają bohaterowie, jest już w rękach kogoś innego.',
        'Pomoc nadchodzi, ale za cenę, której nikt nie chciał płacić.',
        'Prawda obciąża kogoś, komu bohaterowie zdążyli zaufać.',
        'Czas goni: każda zwłoka oznacza, że ucierpi ktoś niewinny.',
        'Dwie strony konfliktu chcą od bohaterów tego samego - i obie grożą.',
        'Pojawia się świadek, który wie za dużo i nie zamierza milczeć za darmo.',
        'Sprawa okazuje się powiązana z większą fabułą - to nie był przypadek.',
    ],

    'kulminacje' => [
        'Wybór bohaterów przesądzi, która ze stron zyska przewagę w {lokacja}.',
        'Okazuje się, że pierwotny zleceniodawca kłamał co do swoich intencji - teraz trzeba zdecydować, co dalej.',
        'Konfrontacja, której nie da się już uniknąć: w grze jest więcej niż początkowa stawka.',
        'Ujawnia się powiązanie z fabułą globalną - decyzja bohaterów odbije się szerzej niż w {lokacja}.',
    ],

    'zakonczenia' => [
        'Pełny sukces - lecz z gorzkim posmakiem albo niespodziewanym kosztem.',
        'Częściowy sukces: jeden cel osiągnięty, drugi przepada lub zostaje na później.',
        'Porażka, która otwiera nowy wątek i dług do spłacenia.',
    ],

    'wskazowki_mg' => [
        'Realia: trzymaj się klimatu renesansu/XV w. i systemu stanowego; waluta to Kraby (KF).',
        'Napięcia tła do wykorzystania: zimna wojna Imperium-Amarth, skutki WDM, uprzedzenia rasowe.',
        'Daj graczom min. 2 realne wybory w kulminacji; konsekwencje notuj na oś czasu postaci.',
    ],
];
