@extends('layouts.app', ['tytul' => 'KF2 Studio - Listingi'])

@section('tresc')

<div class="card">
  <h3>Produkty w bazie</h3>
  @if ($produkty->isEmpty())
    <div class="hint">Brak produktów. Dodaj pierwszy poniżej - to on staje się źródłem prawdy dla wszystkich platform.</div>
  @else
    <table>
      <tr><th>SKU</th><th>Tytuł (EN)</th><th>Status</th><th>Uwagi</th><th></th></tr>
      @foreach ($produkty as $produkt)
        <tr>
          <td>{{ $produkt->sku }}</td>
          <td style="color:#c4cce0">{{ $produkt->tytul_en ?: '—' }}</td>
          <td>{{ $produkt->status }}</td>
          <td>
            @if (($uwagi[$produkt->id] ?? []) === [])
              <span style="color:var(--ok)">czysto</span>
            @else
              <span style="color:var(--warn)">{{ count($uwagi[$produkt->id]) }} do poprawy</span>
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
    <h3>Nowy produkt</h3>
    <div class="field">
      <label for="sku">SKU / identyfikator</label>
      <input type="text" name="sku" id="sku" autocomplete="off" placeholder="np. kf2-castle-doflot" value="{{ old('sku') }}">
    </div>
    <div class="row">
      <div class="field">
        <label for="tytul_pl">Tytuł PL</label>
        <input type="text" name="tytul_pl" id="tytul_pl" autocomplete="off" value="{{ old('tytul_pl') }}">
      </div>
      <div class="field">
        <label for="tytul_en">Tytuł EN</label>
        <input type="text" name="tytul_en" id="tytul_en" autocomplete="off" value="{{ old('tytul_en') }}">
      </div>
    </div>
    <div class="field">
      <label for="opis_pl">Opis PL</label>
      <textarea name="opis_pl" id="opis_pl">{{ old('opis_pl') }}</textarea>
    </div>
    <div class="field">
      <label for="opis_en">Opis EN</label>
      <textarea name="opis_en" id="opis_en">{{ old('opis_en') }}</textarea>
    </div>
    <div class="field">
      <label for="tagi">Tagi (po przecinku)</label>
      <input type="text" name="tagi" id="tagi" autocomplete="off" placeholder="castle, fantasy rpg, tabletop terrain" value="{{ old('tagi') }}">
    </div>
  </div>
  <button type="submit" class="go disp">Dodaj produkt</button>
</form>

<div class="card" style="margin-top:14px">
  <h3>Platformy i ich limity</h3>
  <table>
    <tr><th>Platforma</th><th>Język</th><th>Tytuł</th><th>Opis</th><th>Tagi</th></tr>
    @foreach ($platformy as $platforma)
      <tr>
        <td>{{ $platforma->nazwa }}</td>
        <td>{{ $platforma->jezyk }}</td>
        <td>{{ $platforma->limit_tytulu }}</td>
        <td>{{ $platforma->limit_opisu }}</td>
        <td>{{ $platforma->limit_tagow }}{{ $platforma->format_tagu === 'lowercase' ? ' (lowercase)' : '' }}</td>
      </tr>
    @endforeach
  </table>
  <div class="hint">Limity siedzą w bazie (tabela <code>platformy</code>) - popraw je przy pierwszym realnym eksporcie, bez ruszania kodu.</div>
</div>
@endsection
