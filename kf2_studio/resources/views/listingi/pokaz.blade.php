@extends('layouts.app', ['tytul' => 'KF2 Studio - '.$produkt->sku])

@section('tresc')

@php
    $blokujace = array_values(array_filter($uwagi, fn ($u) => $u['waga'] === 'blokuje'));
    $drobne = array_values(array_filter($uwagi, fn ($u) => $u['waga'] !== 'blokuje'));
@endphp

@if ($uwagi === [])
  <div class="note ok">Kontrola przed publikacją: brak uwag.</div>
@else
  @if ($blokujace !== [])
    <div class="note">
      <b>Blokuje wystawienie ({{ count($blokujace) }}):</b><br>
      @foreach ($blokujace as $uwaga)
        &middot; [{{ $uwaga['pole'] }}] {{ $uwaga['opis'] }}<br>
      @endforeach
    </div>
  @endif
  @if ($drobne !== [])
    <div class="note" style="color:var(--muted);border-color:var(--line);background:#0a0e15">
      <b style="color:var(--warn)">Do rozważenia ({{ count($drobne) }}):</b><br>
      @foreach ($drobne as $uwaga)
        &middot; [{{ $uwaga['pole'] }}] {{ $uwaga['opis'] }}<br>
      @endforeach
    </div>
  @endif
@endif

<form method="post" action="{{ route('listingi.zapisz', $produkt) }}">
  @csrf
  @method('PUT')

  <div class="card">
    <h3>Tożsamość</h3>
    <div class="row">
      <div class="field">
        <label for="sku">SKU (niezmienne)</label>
        <input type="text" name="sku" id="sku" value="{{ $produkt->sku }}" readonly
               style="color:var(--muted)">
      </div>
      <div class="field">
        <label for="wersja">Wersja</label>
        <input type="text" name="wersja" id="wersja" value="{{ $produkt->wersja }}">
      </div>
      <div class="field">
        <label for="status">Status</label>
        <select name="status" id="status">
          @foreach ($statusy as $stan)
            <option value="{{ $stan }}" @selected($produkt->status === $stan)>{{ $stan }}</option>
          @endforeach
        </select>
      </div>
    </div>
    <div class="field">
      <label for="tytul_sprzedazowy">Tytuł sprzedażowy</label>
      <input type="text" name="tytul_sprzedazowy" id="tytul_sprzedazowy" value="{{ $produkt->tytul_sprzedazowy }}">
    </div>
    <div class="field">
      <label for="tytul_krotki">Skrócony tytuł platformowy</label>
      <input type="text" name="tytul_krotki" id="tytul_krotki" value="{{ $produkt->tytul_krotki }}">
      <div class="hint">Używany, gdy pełny tytuł nie mieści się w limicie — zamiast maszynowego cięcia.</div>
    </div>
    <div class="row">
      <div class="field">
        <label for="nazwa_pl">Nazwa PL</label>
        <input type="text" name="nazwa_pl" id="nazwa_pl" value="{{ $produkt->nazwa_pl }}">
      </div>
      <div class="field">
        <label for="nazwa_en">Nazwa EN</label>
        <input type="text" name="nazwa_en" id="nazwa_en" value="{{ $produkt->nazwa_en }}">
      </div>
    </div>
    <div class="row">
      <div class="field">
        <label for="typ_produktu">Typ produktu</label>
        <input type="text" name="typ_produktu" id="typ_produktu" value="{{ $produkt->typ_produktu }}">
      </div>
      <div class="field">
        <label for="kolekcja">Kolekcja</label>
        <input type="text" name="kolekcja" id="kolekcja" value="{{ $produkt->kolekcja }}">
      </div>
      <div class="field">
        <label for="slug">Slug / folder</label>
        <input type="text" name="slug" id="slug" value="{{ $produkt->slug }}">
      </div>
    </div>
  </div>

  <div class="card">
    <h3>Świat</h3>
    <div class="row">
      <div class="field">
        <label for="swiat">Przypisanie</label>
        <select name="swiat" id="swiat">
          <option value="kf2" @selected($produkt->swiat === 'kf2')>KF2</option>
          <option value="niezalezny" @selected($produkt->swiat === 'niezalezny')>Niezależny</option>
          <option value="inny" @selected($produkt->swiat === 'inny')>Inny projekt</option>
        </select>
      </div>
      <div class="field">
        <label for="lokacja">Lokacja</label>
        <input type="text" name="lokacja" id="lokacja" value="{{ $produkt->lokacja }}">
      </div>
      <div class="field">
        <label for="frakcja">Frakcja</label>
        <input type="text" name="frakcja" id="frakcja" value="{{ $produkt->frakcja }}">
      </div>
    </div>
    <div class="row">
      <div class="field">
        <label for="postac">Postać</label>
        <input type="text" name="postac" id="postac" value="{{ $produkt->postac }}">
      </div>
      <div class="field">
        <label for="zrodlo_lore">Źródło lore</label>
        <input type="text" name="zrodlo_lore" id="zrodlo_lore" value="{{ $produkt->zrodlo_lore }}">
      </div>
    </div>
    <div class="field">
      <label for="link_lore">Link do lore</label>
      <input type="text" name="link_lore" id="link_lore" value="{{ $produkt->link_lore }}">
    </div>
  </div>

  <div class="card">
    <h3>Produkcja</h3>
    <div class="note">Sekcja 10: nie deklarujemy skali, testu druku ani braku podpór, jeśli nie zostały sprawdzone.</div>
    <div class="row">
      <div class="field">
        <label for="formaty">Formaty (po przecinku)</label>
        <input type="text" name="formaty" id="formaty" value="{{ implode(', ', $produkt->formaty ?? []) }}"
               placeholder="STL, 3MF, GLB">
      </div>
      <div class="field">
        <label for="liczba_elementow">Liczba elementów</label>
        <input type="text" name="liczba_elementow" id="liczba_elementow" value="{{ $produkt->liczba_elementow }}">
      </div>
    </div>
    <div class="row">
      <div class="field">
        <label for="skala">Skala / wymiary</label>
        <input type="text" name="skala" id="skala" value="{{ $produkt->skala }}" placeholder="45 mm">
      </div>
      <div class="field">
        <label for="technologia">Technologia</label>
        <input type="text" name="technologia" id="technologia" value="{{ $produkt->technologia }}" placeholder="FDM / resin">
      </div>
      <div class="field">
        <label for="stan_testu">Stan testu druku</label>
        <input type="text" name="stan_testu" id="stan_testu" value="{{ $produkt->stan_testu }}"
               placeholder="puste = nieprzetestowane">
      </div>
    </div>
    <div class="field">
      <label for="ustawienia_druku">Ustawienia druku</label>
      <textarea name="ustawienia_druku" id="ustawienia_druku">{{ $produkt->ustawienia_druku }}</textarea>
    </div>
    <label class="check">
      <input type="checkbox" name="wymaga_podpor" value="1" @checked($produkt->wymaga_podpor)>
      Wymaga podpór (zaznacz dopiero po sprawdzeniu — puste znaczy „nie wiadomo")
    </label>
  </div>

  <div class="card">
    <h3>Sprzedaż i licencja</h3>
    <div class="row">
      <div class="field">
        <label for="cena">Cena (USD)</label>
        <input type="text" name="cena" id="cena" value="{{ $produkt->cena }}" placeholder="4.99">
      </div>
      <div class="field">
        <label for="licencja_podstawowa">Licencja podstawowa</label>
        <input type="text" name="licencja_podstawowa" id="licencja_podstawowa" value="{{ $produkt->licencja_podstawowa }}">
      </div>
    </div>
    <div class="row">
      <div class="field">
        <label for="licencja_komercyjna">Licencja komercyjna</label>
        <input type="text" name="licencja_komercyjna" id="licencja_komercyjna" value="{{ $produkt->licencja_komercyjna }}">
      </div>
      <div class="field">
        <label for="limit_sprzedazy">Limit sprzedaży wydruków</label>
        <input type="text" name="limit_sprzedazy" id="limit_sprzedazy" value="{{ $produkt->limit_sprzedazy }}">
      </div>
    </div>
    <label class="check">
      <input type="checkbox" name="platny" value="1" @checked($produkt->platny)>
      Produkt płatny
    </label>
    <div class="field" style="margin-top:12px">
      <label for="zawartosc_zestawu">Zawartość zestawu</label>
      <textarea name="zawartosc_zestawu" id="zawartosc_zestawu">{{ $produkt->zawartosc_zestawu }}</textarea>
    </div>
  </div>

  <div class="card">
    <h3>Treści listingu</h3>
    <div class="field">
      <label for="krotki_opis">Krótki opis</label>
      <textarea name="krotki_opis" id="krotki_opis">{{ $produkt->krotki_opis }}</textarea>
    </div>
    <div class="field">
      <label for="opis_en">Opis EN</label>
      <textarea name="opis_en" id="opis_en">{{ $produkt->opis_en }}</textarea>
    </div>
    <div class="field">
      <label for="opis_pl">Opis PL</label>
      <textarea name="opis_pl" id="opis_pl">{{ $produkt->opis_pl }}</textarea>
    </div>
    <div class="field">
      <label for="opis_cc_cn">Opis zlokalizowany pod Creality Cloud CN</label>
      <textarea name="opis_cc_cn" id="opis_cc_cn">{{ $produkt->opis_cc_cn }}</textarea>
      <div class="hint">Osobna pozycja kompletu metadanych — nie tłumaczymy jej automatycznie.</div>
    </div>
    <div class="field">
      <label for="tagi">Tagi (po przecinku)</label>
      <input type="text" name="tagi" id="tagi" value="{{ implode(', ', $produkt->tagi ?? []) }}">
    </div>
    <div class="row">
      <div class="field">
        <label for="tytul_posta">Tytuł posta</label>
        <input type="text" name="tytul_posta" id="tytul_posta" value="{{ $produkt->tytul_posta }}">
      </div>
    </div>
    <div class="field">
      <label for="cta">CTA</label>
      <textarea name="cta" id="cta">{{ $produkt->cta }}</textarea>
    </div>
  </div>

  <button type="submit" class="go disp">Zapisz wpis</button>
</form>

<div class="card" style="margin-top:14px">
  <h3>Teksty per platforma</h3>
  @foreach ($eksporty as $slug => $eksport)
    <details>
      <summary>{{ $eksport['platforma'] }} ({{ $eksport['jezyk'] }})@if ($eksport['ostrzezenia']) — {{ count($eksport['ostrzezenia']) }} ostrzeżeń @endif</summary>
      @foreach ($eksport['ostrzezenia'] as $ostrzezenie)
        <div class="hint" style="color:var(--warn)">&middot; {{ $ostrzezenie }}</div>
      @endforeach
      <table>
        <tr><td>Tytuł</td><td>{{ $eksport['tytul'] }}</td></tr>
        <tr><td>Tagi</td><td>{{ implode(', ', $eksport['tagi']) }}</td></tr>
        <tr><td>Opis</td><td style="white-space:pre-wrap">{{ $eksport['opis'] }}</td></tr>
      </table>
      <div style="margin:8px 0 4px">
        <a class="mini" href="{{ route('listingi.eksport', [$produkt, $slug]) }}">Pobierz JSON</a>
      </div>
    </details>
  @endforeach
  <div style="margin-top:12px">
    <a class="mini" href="{{ route('listingi.paczka', $produkt) }}">Pobierz 06_THANGS_LISTING (zip)</a>
  </div>
  <div class="hint">
    Zip zawiera komplet plików katalogu <code>06_THANGS_LISTING</code> z paczki Commander V3 —
    wypakuj go wprost do folderu produktu.
  </div>
</div>

@if ($produkt->listingi->isNotEmpty())
  <div class="card">
    <h3>Dystrybucja</h3>
    <table>
      <tr><th>Platforma</th><th>Status</th><th>Link</th><th>Opublikowano</th></tr>
      @foreach ($produkt->listingi as $listing)
        <tr>
          <td>{{ $listing->platforma?->nazwa ?? '—' }}</td>
          <td>{{ $listing->status }}</td>
          <td>{{ $listing->link ? 'jest' : '—' }}</td>
          <td>{{ $listing->data_publikacji?->format('Y-m-d') ?? '—' }}</td>
        </tr>
      @endforeach
    </table>
    <div class="hint">Publikację uznajemy za wykonaną dopiero po otrzymaniu działającego linku (sekcja 13).</div>
  </div>
@endif

<div style="margin-top:12px"><a class="mini" href="{{ route('listingi.index') }}">← Wróć do rejestru</a></div>
@endsection
