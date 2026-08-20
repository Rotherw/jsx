@extends('layouts.app', ['tytul' => 'KF2 Studio - Wiki'])

@section('tresc')
@php
    $typAktywny = $wejscie['typ'] ?? ($typy[0]['klucz'] ?? 'lokacja');
    $polaTypu = collect($typy)->firstWhere('klucz', $typAktywny)['pola'] ?? [];
    $widoczne = fn (string $pole): bool => in_array($pole, $polaTypu, true);
@endphp

<form method="post" action="{{ route('wiki.generuj') }}">
  @csrf
  <div class="card">
    <h3>Generator artykułów</h3>

    <div class="field">
      <label for="typ">Typ artykułu</label>
      <select name="typ" id="typ" onchange="this.form.submit()">
        @foreach ($typy as $typ)
          <option value="{{ $typ['klucz'] }}" @selected($typAktywny === $typ['klucz'])>{{ $typ['etykieta'] }}</option>
        @endforeach
      </select>
      <div class="hint">Zmiana typu przeładowuje formularz - każdy typ ma własny zestaw pól i sekcji.</div>
    </div>

    <div class="field">
      <label for="nazwa">Nazwa</label>
      <input type="text" name="nazwa" id="nazwa" autocomplete="off"
             placeholder="np. Równina Płomieni, Stary Kowal, Bitwa pod Marlua"
             value="{{ $wejscie['nazwa'] ?? '' }}">
    </div>

    <div class="row">
      @if ($widoczne('kontynent'))
        <div class="field">
          <label for="kontynent">Kontynent</label>
          <select name="kontynent" id="kontynent">
            <option value="">- nie podano -</option>
            @foreach ($kanon->lista('kontynent') as $wartosc)
              <option @selected(($wejscie['kontynent'] ?? '') === $wartosc)>{{ $wartosc }}</option>
            @endforeach
            <option value="wlasny" @selected(($wejscie['kontynent'] ?? '') === 'wlasny')>własny (wpisz w zarysie)</option>
          </select>
        </div>
      @endif

      @if ($widoczne('panstwo'))
        <div class="field">
          <label for="panstwo">Państwo / Kraina</label>
          <select name="panstwo" id="panstwo">
            <option value="">- nie podano -</option>
            @foreach ($kanon->lista('panstwo') as $wartosc)
              <option @selected(($wejscie['panstwo'] ?? '') === $wartosc)>{{ $wartosc }}</option>
            @endforeach
            <option value="ziemie_niczyje" @selected(($wejscie['panstwo'] ?? '') === 'ziemie_niczyje')>poza państwami (ziemie niczyje)</option>
          </select>
        </div>
      @endif
    </div>

    <div class="row">
      @if ($widoczne('rasa'))
        <div class="field">
          <label for="rasa">Rasa</label>
          <select name="rasa" id="rasa">
            <option value="">- nie podano -</option>
            @foreach ($kanon->lista('rasa') as $wartosc)
              <option @selected(($wejscie['rasa'] ?? '') === $wartosc)>{{ $wartosc }}</option>
            @endforeach
          </select>
        </div>
      @endif

      @if ($widoczne('rola'))
        <div class="field">
          <label for="rola">Profesja / funkcja</label>
          <input type="text" name="rola" id="rola" autocomplete="off"
                 placeholder="np. kowal, arbiter, dowódca" value="{{ $wejscie['rola'] ?? '' }}">
        </div>
      @endif
    </div>

    <div class="row">
      @if ($widoczne('charakter'))
        <div class="field">
          <label for="charakter">Charakter (alignment)</label>
          <select name="charakter" id="charakter">
            <option value="">- nie podano -</option>
            @foreach ($kanon->lista('charakter') as $wartosc)
              <option @selected(($wejscie['charakter'] ?? '') === $wartosc)>{{ $wartosc }}</option>
            @endforeach
          </select>
        </div>
      @endif

      @if ($widoczne('rok'))
        <div class="field">
          <label for="rok">Rok / data (KF2)</label>
          <input type="text" name="rok" id="rok" autocomplete="off"
                 placeholder="np. 3340 NE, era KE" value="{{ $wejscie['rok'] ?? '' }}">
        </div>
      @endif
    </div>

    <div class="field">
      <label for="zarys">Zarys / znane fakty</label>
      <textarea name="zarys" id="zarys"
                placeholder="Wpisz to, co już wiesz z lore. Generator NIE dopisze faktów od siebie.">{{ $wejscie['zarys'] ?? '' }}</textarea>
    </div>

    <div class="row">
      <div class="field">
        <label for="ton">Ton</label>
        <select name="ton" id="ton">
          <option value="domyslny" @selected(($wejscie['ton'] ?? 'domyslny') === 'domyslny')>Encyklopedyczny</option>
          <option value="klimatyczny" @selected(($wejscie['ton'] ?? '') === 'klimatyczny')>Klimatyczny</option>
          <option value="kronikarski" @selected(($wejscie['ton'] ?? '') === 'kronikarski')>Kronikarski</option>
        </select>
        <div class="hint">Nie każdy typ ma osobny wariant tonu - wtedy używany jest encyklopedyczny.</div>
      </div>
      <div class="field">
        <label for="format">Format wyjścia</label>
        <select name="format" id="format">
          <option value="wiki" @selected(($wejscie['format'] ?? 'wiki') === 'wiki')>Wiki (== ==)</option>
          <option value="tekst" @selected(($wejscie['format'] ?? '') === 'tekst')>Czysty tekst</option>
        </select>
      </div>
    </div>

    <label class="check">
      <input type="checkbox" name="ze_stopka" value="1" @checked($wejscie['ze_stopka'] ?? false)>
      Dodaj stopkę „Świat KF2 - Kroniki Fallathanu (Thoran)”
    </label>
  </div>

  <button type="submit" class="go disp">Generuj artykuł</button>
</form>

@if ($wynik)
  @include('layouts.wynik', ['tresc' => $wynik, 'etykieta' => 'Artykuł wiki', 'id' => 'artykul'])
  <div class="hint">Żółte pola <span style="color:var(--warn)">[UZUPEŁNIJ: ...]</span> to luki do ręcznego wypełnienia kanonem - generator celowo ich nie zmyśla.</div>

  <form method="post" action="{{ route('wiki.zapisz') }}" style="margin-top:12px">
    @csrf
    <input type="hidden" name="typ" value="{{ $wejscie['typ'] ?? '' }}">
    <input type="hidden" name="nazwa" value="{{ ($wejscie['nazwa'] ?? '') ?: 'Bez nazwy' }}">
    <input type="hidden" name="ton" value="{{ $wejscie['ton'] ?? 'domyslny' }}">
    <input type="hidden" name="format" value="{{ $wejscie['format'] ?? 'wiki' }}">
    <input type="hidden" name="ze_stopka" value="{{ ($wejscie['ze_stopka'] ?? false) ? 1 : 0 }}">
    <input type="hidden" name="tresc" value="{{ $wynik }}">
    <button type="submit" class="go alt disp">Zapisz w bazie</button>
  </form>
@endif

<div class="card" style="margin-top:14px">
  <h3>Szybki kanon KF2</h3>
  <table>
    @foreach ($kanon->fakty() as $fakt)
      <tr><td>{{ $fakt['etykieta'] }}</td><td>{{ $fakt['wartosc'] }}</td></tr>
    @endforeach
  </table>
  <div class="hint">To skrót pomocniczy. Pełny i wiążący kanon: <a href="{{ config('kf2.wiki_url') }}">{{ config('kf2.wiki_url') }}</a>. Czego nie ma w wiki - dopytaj Thorana, nie zgaduj.</div>
</div>

@if ($artykuly->isNotEmpty())
  <div class="card">
    <h3>Ostatnio zapisane artykuły</h3>
    <table>
      <tr><th>Nazwa</th><th>Typ</th><th>Stan</th><th>Zapisano</th></tr>
      @foreach ($artykuly as $artykul)
        <tr>
          <td>{{ $artykul->nazwa }}</td>
          <td>{{ $artykul->typ_klucz }}</td>
          <td>{{ $artykul->ma_luki ? 'ma luki' : 'kompletny' }}</td>
          <td>{{ $artykul->created_at?->format('Y-m-d H:i') }}</td>
        </tr>
      @endforeach
    </table>
  </div>
@endif
@endsection
