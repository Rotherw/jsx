@extends('layouts.app', ['tytul' => 'KF2 Studio - '.$produkt->sku])

@section('tresc')

@if ($uwagi === [])
  <div class="note ok">Kontrola spójności: brak uwag.</div>
@else
  <div class="note">
    <b>Kontrola spójności - {{ count($uwagi) }} {{ count($uwagi) === 1 ? 'uwaga' : 'uwag' }}:</b><br>
    @foreach ($uwagi as $uwaga)
      &middot; [{{ $uwaga['pole'] }}] {{ $uwaga['opis'] }}<br>
    @endforeach
  </div>
@endif

<form method="post" action="{{ route('listingi.zapisz', $produkt) }}">
  @csrf
  @method('PUT')
  <div class="card">
    <h3>{{ $produkt->sku }}</h3>
    <div class="field">
      <label for="sku">SKU</label>
      <input type="text" name="sku" id="sku" value="{{ $produkt->sku }}">
    </div>
    <div class="row">
      <div class="field">
        <label for="tytul_pl">Tytuł PL</label>
        <input type="text" name="tytul_pl" id="tytul_pl" value="{{ $produkt->tytul_pl }}">
      </div>
      <div class="field">
        <label for="tytul_en">Tytuł EN</label>
        <input type="text" name="tytul_en" id="tytul_en" value="{{ $produkt->tytul_en }}">
      </div>
    </div>
    <div class="field">
      <label for="opis_pl">Opis PL</label>
      <textarea name="opis_pl" id="opis_pl">{{ $produkt->opis_pl }}</textarea>
    </div>
    <div class="field">
      <label for="opis_en">Opis EN</label>
      <textarea name="opis_en" id="opis_en">{{ $produkt->opis_en }}</textarea>
    </div>
    <div class="row">
      <div class="field">
        <label for="tagi">Tagi (po przecinku)</label>
        <input type="text" name="tagi" id="tagi" value="{{ implode(', ', $produkt->tagi ?? []) }}">
      </div>
      <div class="field">
        <label for="status">Status</label>
        <input type="text" name="status" id="status" value="{{ $produkt->status }}">
      </div>
    </div>
  </div>
  <button type="submit" class="go disp">Zapisz zmiany</button>
</form>

<div class="card" style="margin-top:14px">
  <h3>Podgląd eksportu per platforma</h3>
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
  <div class="hint">Eksport jest wyliczany z rekordu produktu - popraw raz tutaj, a wszystkie platformy dostaną spójną wersję.</div>
</div>

<div style="margin-top:12px"><a class="mini" href="{{ route('listingi.index') }}">← Wróć do listy</a></div>
@endsection
