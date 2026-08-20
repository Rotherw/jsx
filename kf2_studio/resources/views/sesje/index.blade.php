@extends('layouts.app', ['tytul' => 'KF2 Studio - Sesje'])

@section('tresc')
@php
    $wybrane = (array) ($wejscie['motywy'] ?? []);
@endphp

<form method="post" action="{{ route('sesje.generuj') }}">
  @csrf
  <div class="card">
    <h3>Generator sesji</h3>

    <div class="field">
      <label for="tytul">Tytuł sesji (puste = wygeneruje)</label>
      <input type="text" name="tytul" id="tytul" autocomplete="off"
             placeholder="np. Cienie nad Marlua" value="{{ $wejscie['tytul'] ?? '' }}">
    </div>

    <div class="row">
      <div class="field">
        <label for="rodzaj">Rodzaj Opowieści</label>
        <select name="rodzaj" id="rodzaj">
          @foreach ($slownik['rodzaje'] as $rodzaj)
            <option value="{{ $rodzaj['klucz'] }}" @selected(($wejscie['rodzaj'] ?? 'fg') === $rodzaj['klucz'])>{{ $rodzaj['etykieta'] }}</option>
          @endforeach
        </select>
      </div>
      <div class="field">
        <label for="skala">Skala</label>
        <select name="skala" id="skala">
          @foreach ($slownik['skale'] as $skala)
            <option value="{{ $skala['klucz'] }}" @selected(($wejscie['skala'] ?? 'druzyna') === $skala['klucz'])>{{ $skala['etykieta'] }}</option>
          @endforeach
        </select>
      </div>
    </div>

    <div class="field">
      <label>Motyw (1-2)</label>
      <div class="chips">
        @foreach ($slownik['motywy'] as $motyw)
          <label>
            <input type="checkbox" name="motywy[]" value="{{ $motyw['klucz'] }}" @checked(in_array($motyw['klucz'], $wybrane, true))>
            {{ $motyw['etykieta'] }}
          </label>
        @endforeach
      </div>
      <div class="hint">Nic nie zaznaczysz - motyw zostanie wylosowany. Liczą się pierwsze dwa.</div>
    </div>

    <div class="row">
      <div class="field">
        <label for="panstwo">Państwo / Kraina</label>
        <select name="panstwo" id="panstwo">
          <option value="">- dowolne -</option>
          @foreach ($kanon->lista('panstwo') as $wartosc)
            <option @selected(($wejscie['panstwo'] ?? '') === $wartosc)>{{ $wartosc }}</option>
          @endforeach
        </select>
      </div>
      <div class="field">
        <label for="miejsce">Miejsce (opcja)</label>
        <input type="text" name="miejsce" id="miejsce" list="lokacje" autocomplete="off"
               placeholder="np. Marlua, Aurea, Vipera" value="{{ $wejscie['miejsce'] ?? '' }}">
        <datalist id="lokacje">
          @foreach ($kanon->lista('lokacja') as $wartosc)
            <option>{{ $wartosc }}</option>
          @endforeach
        </datalist>
      </div>
    </div>

    <div class="row">
      <div class="field">
        <label for="frakcja">Frakcja / rasa w centrum (opcja)</label>
        <select name="frakcja" id="frakcja">
          <option value="">- brak -</option>
          @foreach ($kanon->lista('frakcja') as $wartosc)
            <option @selected(($wejscie['frakcja'] ?? '') === $wartosc)>{{ $wartosc }}</option>
          @endforeach
        </select>
      </div>
      <div class="field">
        <label for="dlugosc">Długość</label>
        <select name="dlugosc" id="dlugosc">
          @foreach ($slownik['dlugosci'] as $dlugosc)
            <option value="{{ $dlugosc['klucz'] }}" @selected(($wejscie['dlugosc'] ?? 'one_shot') === $dlugosc['klucz'])>{{ $dlugosc['etykieta'] }}</option>
          @endforeach
        </select>
      </div>
    </div>

    <div class="field">
      <label for="ton">Ton</label>
      <select name="ton" id="ton">
        @foreach ($slownik['tony'] as $ton)
          <option value="{{ $ton['klucz'] }}" @selected(($wejscie['ton'] ?? 'heroiczny') === $ton['klucz'])>{{ $ton['etykieta'] }}</option>
        @endforeach
      </select>
    </div>

    <div class="field">
      <label for="fabula">Powiązanie z aktualną fabułą / Wieściami (opcja)</label>
      <textarea name="fabula" id="fabula"
                placeholder="Wpisz bieżące wydarzenia FG, które sesja ma uwzględniać. Generator wplecie to jako kontekst, ale nie wymyśli nowego kanonu.">{{ $wejscie['fabula'] ?? '' }}</textarea>
    </div>

    <label class="check">
      <input type="checkbox" name="wskazowki_mg" value="1" @checked($wejscie['wskazowki_mg'] ?? true)>
      Dodawaj sekcję „Wskazówki dla prowadzącego”
    </label>

    <div class="field" style="margin-top:12px">
      <label for="ziarno">Ziarno (puste = nowy wariant)</label>
      <input type="text" name="ziarno" id="ziarno" autocomplete="off" value="">
      <div class="hint">Wpisz ziarno zapisanej sesji, żeby odtworzyć dokładnie ten sam szkielet.</div>
    </div>
  </div>

  <button type="submit" class="go disp">Generuj sesję</button>
</form>

@if ($wynik)
  @include('layouts.wynik', ['tresc' => $wynik, 'etykieta' => 'Szkielet sesji', 'id' => 'sesja'])
  <div class="hint">
    Ziarno tego wariantu: <b>{{ $ziarno }}</b>. Żółte <span style="color:var(--warn)">[UZUPEŁNIJ: ...]</span> = decyzje prowadzącego
    albo twardy kanon do potwierdzenia. Reszta to propozycje - klikaj <b>Generuj</b> ponownie po inny wariant.
  </div>

  <form method="post" action="{{ route('sesje.zapisz') }}" style="margin-top:12px">
    @csrf
    @foreach (['tytul', 'rodzaj', 'skala', 'dlugosc', 'panstwo', 'miejsce', 'frakcja', 'ton', 'fabula'] as $pole)
      <input type="hidden" name="{{ $pole }}" value="{{ $wejscie[$pole] ?? '' }}">
    @endforeach
    @foreach ((array) ($wejscie['motywy'] ?? []) as $motyw)
      <input type="hidden" name="motywy[]" value="{{ $motyw }}">
    @endforeach
    <input type="hidden" name="wskazowki_mg" value="{{ ($wejscie['wskazowki_mg'] ?? true) ? 1 : 0 }}">
    <input type="hidden" name="ziarno" value="{{ $ziarno }}">
    <input type="hidden" name="tresc" value="{{ $wynik }}">
    <input type="hidden" name="tytul_wyniku" value="{{ trim(ltrim(strtok($wynik, "\n"), '# ')) ?: 'Sesja bez tytułu' }}">
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
  <div class="hint">Sesje FG muszą zgadzać się z Wieściami - czego nie ma w <a href="{{ config('kf2.wiki_url') }}">wiki</a>, ustal z Thoranem.</div>
</div>

@if ($sesje->isNotEmpty())
  <div class="card">
    <h3>Ostatnio zapisane sesje</h3>
    <table>
      <tr><th>Tytuł</th><th>Rodzaj</th><th>Ziarno</th><th>Zapisano</th></tr>
      @foreach ($sesje as $sesja)
        <tr>
          <td>{{ $sesja->tytul }}</td>
          <td>{{ $sesja->rodzaj }}</td>
          <td>{{ $sesja->ziarno }}</td>
          <td>{{ $sesja->created_at?->format('Y-m-d H:i') }}</td>
        </tr>
      @endforeach
    </table>
  </div>
@endif
@endsection
