@extends('layouts.app', ['tytul' => 'KF2 Studio - Rejestr modeli'])

@section('tresc')

<div class="card">
  <h3>Rejestr modeli</h3>
  @if ($produkty->isEmpty())
    <div class="hint">Rejestr jest pusty. Dodaj pierwszy wpis poniżej — to on staje się źródłem prawdy dla wszystkich platform.</div>
  @else
    <table>
      <tr><th>SKU</th><th>Tytuł sprzedażowy</th><th>Status</th><th>Kontrola</th><th></th></tr>
      @foreach ($produkty as $produkt)
        @php $lista = $uwagi[$produkt->id] ?? []; @endphp
        <tr>
          <td>{{ $produkt->sku }}</td>
          <td style="color:#c4cce0">{{ $produkt->tytul_sprzedazowy ?: '—' }}</td>
          <td>{{ $produkt->status }}</td>
          <td>
            @if ($lista === [])
              <span style="color:var(--ok)">czysto</span>
            @elseif ($linter->blokuje($lista))
              <span style="color:var(--rose)">blokuje ({{ count($lista) }})</span>
            @else
              <span style="color:var(--warn)">{{ count($lista) }} uwag</span>
            @endif
          </td>
          <td><a class="mini" href="{{ route('listingi.pokaz', $produkt) }}">Otwórz</a></td>
        </tr>
      @endforeach
    </table>
  @endif
</div>

<form method="post" action="{{ route('listingi.utworz') }}">
  @csrf
  <div class="card">
    <h3>Nowy wpis</h3>
    <div class="note">SKU po nadaniu nie zmienia się i nie może zostać użyte ponownie (system v2.0, sekcja 7).</div>
    <div class="row">
      <div class="field">
        <label for="sku">SKU</label>
        <input type="text" name="sku" id="sku" autocomplete="off" placeholder="np. KF2-CASTLE-DOFLOT-001" value="{{ old('sku') }}">
      </div>
      <div class="field">
        <label for="swiat">Świat</label>
        <select name="swiat" id="swiat">
          <option value="kf2" @selected(old('swiat', 'kf2') === 'kf2')>KF2</option>
          <option value="niezalezny" @selected(old('swiat') === 'niezalezny')>Niezależny</option>
          <option value="inny" @selected(old('swiat') === 'inny')>Inny projekt</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label for="tytul_sprzedazowy">Tytuł sprzedażowy</label>
      <input type="text" name="tytul_sprzedazowy" id="tytul_sprzedazowy" autocomplete="off"
             placeholder="KF2 [Model Name] - [Search Descriptor] - WorkShop3D" value="{{ old('tytul_sprzedazowy') }}">
      <div class="hint">Wzorzec z sekcji 8. Prefiks „KF2" tylko dla produktów KF2.</div>
    </div>
    <div class="row">
      <div class="field">
        <label for="nazwa_pl">Nazwa kanoniczna PL</label>
        <input type="text" name="nazwa_pl" id="nazwa_pl" autocomplete="off" value="{{ old('nazwa_pl') }}">
      </div>
      <div class="field">
        <label for="nazwa_en">Nazwa kanoniczna EN</label>
        <input type="text" name="nazwa_en" id="nazwa_en" autocomplete="off" value="{{ old('nazwa_en') }}">
      </div>
    </div>
    <div class="field">
      <label for="licencja_podstawowa">Licencja podstawowa</label>
      <input type="text" name="licencja_podstawowa" id="licencja_podstawowa" autocomplete="off"
             placeholder="np. Personal Use" value="{{ old('licencja_podstawowa') }}">
      <div class="hint">Jedna licencja obowiązująca na wszystkich platformach (sekcja 11).</div>
    </div>
    <div class="field">
      <label for="link_lore">Link do lore</label>
      <input type="text" name="link_lore" id="link_lore" autocomplete="off"
             placeholder="https://wiki.kf2.pl/..." value="{{ old('link_lore') }}">
      <div class="hint">Produkt KF2 bez źródła lore nie przejdzie kontroli (sekcja 10).</div>
    </div>
  </div>
  <button type="submit" class="go disp">Dodaj do rejestru</button>
</form>

<div class="card" style="margin-top:14px">
  <h3>Platformy</h3>
  <table>
    <tr><th>#</th><th>Platforma</th><th>Kod</th><th>Tytuł</th><th>Opis</th><th>Tagi</th><th>Limity</th></tr>
    @foreach ($platformy as $platforma)
      <tr>
        <td>{{ $platforma->domyslna ? $platforma->priorytet : '—' }}</td>
        <td style="color:{{ $platforma->domyslna ? 'var(--rose)' : 'var(--muted)' }}">{{ $platforma->nazwa }}</td>
        <td>{{ $platforma->kod_pliku }}</td>
        <td>{{ $platforma->limit_tytulu }}</td>
        <td>{{ $platforma->limit_opisu }}</td>
        <td>{{ $platforma->limit_tagow }}{{ $platforma->format_tagu === 'lowercase' ? ' (lowercase)' : '' }}</td>
        <td>{!! $platforma->limity_potwierdzone
            ? '<span style="color:var(--ok)">potwierdzone</span>'
            : '<span style="color:var(--warn)">do sprawdzenia</span>' !!}</td>
      </tr>
    @endforeach
  </table>
  <div class="hint">
    Numer = priorytet z sekcji 13; „—" oznacza platformę przygotowywaną tylko na osobne polecenie.
    Limity oznaczone „do sprawdzenia" są orientacyjne — sekcja 13 zabrania opierać się ślepo na starych
    limitach tagów. Po pierwszym realnym wystawieniu popraw je w tabeli <code>platformy</code>.
  </div>
</div>
@endsection
