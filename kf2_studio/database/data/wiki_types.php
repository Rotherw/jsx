<?php

/**
 * Typy artykulow Wiki Fallathanu + szkielety sekcji.
 *
 * Zrodlo: KF2-Wiki-Generator-Artykulow.html (funkcja sections() + leadXxx()).
 *
 * Skladnia szablonu (patrz App\Domain\Template):
 *   {pole}                 - wartosc pola, pusty string gdy brak
 *   {pole|tekst}           - wartosc pola albo literalny tekst zapasowy
 *   {@opis}                - luka do recznego wypelnienia: [UZUPEŁNIJ: opis]
 *   [[pole? A||B]]       - A gdy pole niepuste, w przeciwnym razie B
 *   [[pole? A]]            - A gdy pole niepuste, inaczej nic
 *
 * Dostepne pola: nazwa, kontynent, panstwo, rasa, rola, charakter, rok,
 *                zarys, gdzie (panstwo + kontynent zlaczone przecinkiem).
 */
return [
    [
        'klucz' => 'lokacja',
        'etykieta' => 'Lokacja',
        'pola' => ['kontynent', 'panstwo'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa}[[gdzie? — lokacja w {gdzie}||— lokacja w Fallathanie]]. {zarys|@jedno zdanie: czym jest ta lokacja}',
            'klimatyczny' => '{nazwa|@nazwa} — miejsce, które na długo zostaje w pamięci tych, co je odwiedzili[[gdzie?, leżące w {gdzie}]]. {zarys|@jednozdaniowy, klimatyczny zarys czym jest to miejsce}',
            'kronikarski' => 'Pod nazwą {nazwa|@nazwa} kroniki wymieniają miejsce w {gdzie|Fallathanie}. {zarys|@zwięzłe, kronikarskie wprowadzenie}',
        ],
        'sekcje' => [
            ['1. Położenie', '[[gdzie?Położenie: {gdzie}. {@dokładne usytuowanie — względem znanych lokacji, kierunki, ukształtowanie terenu}||{@położenie geograficzne — kraina, kontynent, względem czego}]]'],
            ['2. Opis', '{zarys|@wygląd i atmosfera — architektura, materiały, otoczenie, co rzuca się w oczy}'],
            ['3. Historia', '{@historia lokacji — powstanie, kluczowe wydarzenia, zmiany właścicieli}'],
            ['4. Mieszkańcy i frakcje', '{@kto tu mieszka/zarządza, ważne postacie, organizacje}'],
            ['5. Uwagi / ciekawostki', '{@związki z Fabułą Główną, sekrety, niebezpieczeństwa}'],
        ],
    ],
    [
        'klucz' => 'panstwo',
        'etykieta' => 'Państwo / Kraina',
        'pola' => ['kontynent'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa} — państwo[[kontynent? na kontynencie {kontynent}||w Fallathanie]]. {zarys|@jedno-dwa zdania: charakter państwa, czym się wyróżnia}',
        ],
        'sekcje' => [
            ['Geografia i klimat', '{zarys|@położenie na {kontynent|kontynencie}, krajobraz, klimat, granice}'],
            ['Ustrój i władza', '{@forma rządów, kto sprawuje władzę, sukcesja, stolica}'],
            ['Społeczeństwo i stany', '{@system stanowy, dominujące rasy, status innych ras, niewolnictwo/tolerancja}'],
            ['Stosunek do magii', '{@czy magia tolerowana/zakazana, stosunek do magów}'],
            ['Religia', '{@dominujące kulty, stosunek do Przedwiecznego i Bóstw}'],
            ['Podział administracyjny', '{@prowincje/księstwa/regiony i ich specyfika}'],
            ['Historia', '{@powstanie państwa, kluczowe wojny i wydarzenia, lata NE}'],
            ['Stosunki zewnętrzne', '{@sojusze i konflikty z innymi państwami}'],
        ],
    ],
    [
        'klucz' => 'rasa',
        'etykieta' => 'Rasa',
        'pola' => [],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa rasy} — jedna z ras zamieszkujących Fallathan. {@jedno zdanie: skąd pochodzi i czym się wyróżnia}',
        ],
        'sekcje' => [
            ['Pochodzenie', '{@które Bóstwo sprowadziło/stworzyło rasę i jaki cel jej nadało (lub związek z Przedwiecznym)}'],
            ['Wygląd', '{zarys|@cechy fizyczne, wzrost, charakterystyczne elementy}'],
            ['Charakter i kultura', '{@usposobienie, wartości, czy rasa ma własną wyrazistą kulturę}'],
            ['Zdolności i słabości', '{@wrodzone zdolności, odporności, słabości typowe dla rasy}'],
            ['Historia', '{@dzieje rasy w Fallathanie}'],
            ['Występowanie', '{@gdzie zamieszkuje — państwa, regiony}'],
        ],
    ],
    [
        'klucz' => 'postac',
        'etykieta' => 'Postać (NPC)',
        'pola' => ['panstwo', 'rasa', 'rola', 'charakter', 'rok'],
        'lead' => [
            'domyslny' => '{nazwa|@imię}[[rola?, {rola}]][[panstwo? z {panstwo}]][[rasa? ({rasa})]]. {zarys|@jedno zdanie wprowadzające postać}',
        ],
        'sekcje' => [
            ['Karta postaci', "Miano: {nazwa|@imię}\nRasa: {rasa|@rasa}\nWiek: {@wiek}\nProfesja: {rola|@profesja}\nCharakter: {charakter|@alignment}\nStanowisko: {@zajmowane stanowisko / przynależność}[[panstwo?\nPochodzenie: {panstwo}]][[rok?\nWzmiankowany: {rok}]]"],
            ['Wygląd', '{zarys|@opis wyglądu}'],
            ['Charakter', '{@osobowość, motywacje, sposób bycia}'],
            ['Historia postaci', '{@pochodzenie, kluczowe wydarzenia z osi czasu (lata NE)}'],
            ['Powiązania', '{@rodzina, sojusznicy, wrogowie, organizacje}'],
        ],
    ],
    [
        'klucz' => 'wydarzenie',
        'etykieta' => 'Wydarzenie / Wieść',
        'pola' => ['panstwo', 'rok'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa}[[rok? ({rok})]][[panstwo?, {panstwo}]] — wydarzenie w dziejach Fallathanu. {zarys|@jedno zdanie: co to było i dlaczego ważne}',
            'kronikarski' => '{nazwa|@nazwa}[[rok? ({rok})]][[panstwo?, {panstwo}]] — wydarzenie odnotowane w kronikach Fallathanu. {zarys|@jedno zdanie: co to było i dlaczego ważne}',
        ],
        'sekcje' => [
            ['Przebieg', '{zarys|@co się wydarzyło — kolejne etapy}'],
            ['Strony i uczestnicy', '{@kto brał udział — postacie, frakcje, państwa}'],
            ['Skutki', '{@następstwa dla świata/regionu; czy kanoniczne (Wieść)}'],
            ['Powiązania', '{@powiązane lokacje, postacie, wcześniejsze/późniejsze wydarzenia}'],
        ],
    ],
    [
        'klucz' => 'organizacja',
        'etykieta' => 'Organizacja / Frakcja',
        'pola' => ['panstwo'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa} — organizacja[[panstwo? działająca w {panstwo}||w Fallathanie]]. {zarys|@jedno zdanie: czym jest i czym się zajmuje}',
        ],
        'sekcje' => [
            ['Cele', '{zarys|@po co istnieje, czym się zajmuje}'],
            ['Struktura', '{@hierarchia, rangi, zasady członkostwa}'],
            ['Członkowie', '{@ważne postacie, liczebność}'],
            ['Siedziba', '[[panstwo?{@gdzie działa (np. {panstwo})}||{@gdzie działa}]]'],
            ['Historia', '{@założenie i dzieje}'],
        ],
    ],
    [
        'klucz' => 'bostwo',
        'etykieta' => 'Bóstwo',
        'pola' => [],
        'lead' => [
            'domyslny' => '{nazwa|@imię} — jedno z Bóstw Fallathanu, powołanych w ramach Planu Przedwiecznego. {zarys|@jedno zdanie: domena i znaczenie}',
        ],
        'sekcje' => [
            ['Domena i symbolika', '{zarys|@czym włada, symbole, atrybuty}'],
            ['Pozycja wobec Przedwiecznego', '{@rola w panteonie, relacja do Przedwiecznego i innych Bóstw}'],
            ['Kult i wyznawcy', '{@kto czci, gdzie, obrzędy}'],
            ['Mity', '{@związane legendy i opowieści}'],
        ],
    ],
    [
        'klucz' => 'bestia',
        'etykieta' => 'Bestia / Stwór',
        'pola' => ['panstwo'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa} — stwór występujący w Fallathanie. {zarys|@jedno zdanie: co to za istota}',
            'klimatyczny' => '{nazwa|@nazwa} — stworzenie, o którym krąży niejedna mrożąca krew opowieść. {zarys|@jedno zdanie: co to za istota}',
        ],
        'sekcje' => [
            ['Wygląd', '{zarys|@opis fizyczny, rozmiar, cechy szczególne}'],
            ['Zachowanie i środowisko', '{@tryb życia, gdzie występuje, pożywienie}'],
            ['Zagrożenie', '{@jak niebezpieczna, sposoby walki/obrony}'],
            ['Występowanie', '[[panstwo?{@regiony/państwa (np. {panstwo})}||{@regiony/państwa}]]'],
        ],
    ],
    [
        'klucz' => 'artefakt',
        'etykieta' => 'Artefakt',
        'pola' => ['panstwo'],
        'lead' => [
            'domyslny' => '{nazwa|@nazwa} — artefakt znany w Fallathanie. {zarys|@jedno zdanie: czym jest i czemu ważny}',
            'klimatyczny' => '{nazwa|@nazwa} — przedmiot owiany legendą. {zarys|@jedno zdanie: czym jest i czemu ważny}',
        ],
        'sekcje' => [
            ['Wygląd', '{zarys|@jak wygląda, z czego wykonany}'],
            ['Właściwości / moc', '{@działanie, ograniczenia, koszt użycia}'],
            ['Historia', '{@kto stworzył, dzieje, właściciele}'],
            ['Obecne miejsce', '[[panstwo?{@gdzie się znajduje (np. {panstwo})}||{@gdzie się znajduje}]]'],
        ],
    ],
];
