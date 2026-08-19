{{-- Wspolny blok wyniku: podswietla luki i naglowki, pozwala kopiowac. --}}
@php
    $bezpieczny = e($tresc);
    $bezpieczny = preg_replace('/\[UZUPEŁNIJ:[^\]]*\]/u', '<span class="ph">$0</span>', $bezpieczny);
    $bezpieczny = preg_replace('/^(==[^\n]*==|=[^\n]*=|#[^\n]*)$/mu', '<span class="hd">$0</span>', $bezpieczny);
@endphp
<div class="out">
  <div class="out-h">
    <span class="ttl">{{ $etykieta }}</span>
    <button type="button" class="copy" data-kopiuj="{{ $id }}">Kopiuj</button>
  </div>
  <pre id="{{ $id }}" data-raw="{{ $tresc }}">{!! $bezpieczny !!}</pre>
</div>
