<?php

/**
 * Profile platform sprzedazowych WorkShop3D.
 *
 * UWAGA: limity znakow to wartosci startowe do zweryfikowania przy pierwszym
 * realnym eksporcie na kazda platforme - siedza w bazie wlasnie po to, zeby
 * dalo sie je poprawic bez ruszania kodu (tabela platforms).
 */
return [
    [
        'slug' => 'thangs',
        'nazwa' => 'Thangs',
        'jezyk' => 'en',
        'limit_tytulu' => 100,
        'limit_opisu' => 5000,
        'limit_tagow' => 20,
        'format_tagu' => 'swobodny',
        'markdown' => true,
        'uwagi' => 'Opis w Markdown. Tagi wielowyrazowe dozwolone.',
    ],
    [
        'slug' => 'cults3d',
        'nazwa' => 'Cults3D',
        'jezyk' => 'en',
        'limit_tytulu' => 80,
        'limit_opisu' => 4000,
        'limit_tagow' => 10,
        'format_tagu' => 'lowercase',
        'markdown' => false,
        'uwagi' => 'Zwiezle tagi jednowyrazowe daja najlepsze wyniki w wyszukiwarce.',
    ],
    [
        'slug' => 'creality_cn',
        'nazwa' => 'Creality Cloud (CN)',
        'jezyk' => 'en',
        'limit_tytulu' => 60,
        'limit_opisu' => 2000,
        'limit_tagow' => 10,
        'format_tagu' => 'lowercase',
        'markdown' => false,
        'uwagi' => 'Wersja CN - krotsze opisy, bez linkow zewnetrznych.',
        'linki_zewnetrzne' => false,
    ],
    [
        'slug' => 'creality_int',
        'nazwa' => 'Creality Cloud (INT)',
        'jezyk' => 'en',
        'limit_tytulu' => 60,
        'limit_opisu' => 2000,
        'limit_tagow' => 10,
        'format_tagu' => 'lowercase',
        'markdown' => false,
        'uwagi' => 'Wersja miedzynarodowa.',
    ],
    [
        'slug' => 'myminifactory',
        'nazwa' => 'MyMiniFactory',
        'jezyk' => 'en',
        'limit_tytulu' => 100,
        'limit_opisu' => 6000,
        'limit_tagow' => 15,
        'format_tagu' => 'swobodny',
        'markdown' => true,
        'uwagi' => '',
    ],
    [
        'slug' => 'printables',
        'nazwa' => 'Printables',
        'jezyk' => 'en',
        'limit_tytulu' => 60,
        'limit_opisu' => 8000,
        'limit_tagow' => 10,
        'format_tagu' => 'lowercase',
        'markdown' => true,
        'uwagi' => 'Tagi bez spacji - spacje zamieniane na myslniki.',
    ],
];
