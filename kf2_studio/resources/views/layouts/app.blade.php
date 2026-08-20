<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ $tytul ?? 'KF2 Studio' }}</title>
<style>
  :root{
    --bg:#0c1018; --panel:#151c27; --panel2:#0f151f; --ink:#eceef3; --muted:#828c9e; --line:#26303f;
    --wine:#8d2b3a; --rose:#c54a5b; --gold:#d9a441; --blue:#1976d2; --sky:#4a9eea;
    --ok:#3fb96a; --warn:#e0a13a; --r:13px;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0}
  body{background:radial-gradient(1000px 480px at 50% -10%, #17223a 0%, rgba(23,34,58,0) 58%), var(--bg);
    color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,Roboto,Arial,sans-serif;
    line-height:1.5;padding:16px 16px 60px;max-width:900px;margin:0 auto}
  .disp{font-family:"Arial Black","Helvetica Neue",system-ui,sans-serif}
  a{color:var(--sky)}
  .head{display:flex;align-items:center;gap:13px;justify-content:center;margin:4px 0 14px}
  .badge{width:50px;height:50px;border-radius:12px;display:grid;place-items:center;color:#fff;font-size:17px;font-weight:900;
    background:linear-gradient(160deg,var(--wine),#5e1822);box-shadow:0 6px 16px rgba(141,43,58,.4),inset 0 1px 0 rgba(255,255,255,.18)}
  .head .t{font-size:16px;letter-spacing:1px;text-transform:uppercase;color:var(--rose);text-align:left}
  .head .t small{display:block;font-size:11px;letter-spacing:.4px;color:var(--muted);text-transform:none;font-weight:400;margin-top:2px}

  .tabs{display:flex;gap:6px;background:#0a0e15;border:1px solid var(--line);border-radius:12px;padding:5px;margin-bottom:14px;position:sticky;top:8px;z-index:5}
  .tabs a{flex:1;text-align:center;text-decoration:none;color:var(--muted);padding:11px 8px;border-radius:9px;font-size:13.5px;font-weight:700}
  .tabs a.on{background:linear-gradient(160deg,var(--wine),#5e1822);color:#fff;box-shadow:0 4px 12px rgba(141,43,58,.3)}

  .card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:var(--r);padding:14px;margin-bottom:13px}
  .card h3{margin:0 0 11px;font-size:12.5px;letter-spacing:.7px;text-transform:uppercase;color:var(--gold)}
  label{display:block;font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:0 0 6px}
  .field{margin-bottom:12px}
  input[type=text],select,textarea{width:100%;background:#0a0e15;border:1px solid var(--line);color:var(--ink);border-radius:10px;
    padding:11px 12px;font-size:15px;font-family:inherit;outline:none}
  textarea{min-height:74px;resize:vertical;line-height:1.5}
  input:focus,select:focus,textarea:focus{border-color:var(--rose);box-shadow:0 0 0 3px rgba(197,74,91,.14)}
  .row{display:flex;gap:10px;flex-wrap:wrap}.row>.field{flex:1;min-width:150px;margin-bottom:12px}
  .chips{display:flex;flex-wrap:wrap;gap:7px}
  .chips label{border:1px solid var(--line);background:#0a0e15;color:var(--muted);border-radius:999px;padding:8px 13px;
    font-size:12.5px;cursor:pointer;text-transform:none;letter-spacing:0;margin:0;display:inline-flex;align-items:center;gap:7px}
  .chips input{accent-color:var(--rose)}
  .check{display:flex;align-items:center;gap:9px;cursor:pointer;font-size:14px;color:var(--ink);text-transform:none;letter-spacing:0;margin:2px 0}
  .check input{width:18px;height:18px;accent-color:var(--gold)}
  .go{width:100%;border:0;border-radius:12px;padding:15px;font-size:15.5px;font-weight:900;letter-spacing:.4px;text-transform:uppercase;
    color:#fff;cursor:pointer;background:linear-gradient(160deg,var(--wine),#5e1822);box-shadow:0 8px 20px rgba(141,43,58,.32);font-family:inherit}
  .go.alt{background:linear-gradient(160deg,var(--blue),#0d4d92);box-shadow:0 8px 20px rgba(25,118,210,.3)}
  .mini{border:1px solid var(--line);background:#0a0e15;color:var(--muted);font-weight:600;border-radius:10px;padding:9px 13px;
    font-size:12.5px;cursor:pointer;font-family:inherit;text-decoration:none;display:inline-block}
  .hint{font-size:11.5px;color:#6b7790;margin-top:5px;line-height:1.45}
  .note{font-size:12.5px;color:var(--warn);background:rgba(224,161,58,.08);border:1px solid rgba(224,161,58,.3);
    border-radius:9px;padding:9px 11px;margin-bottom:12px}
  .note.ok{color:var(--ok);background:rgba(63,185,106,.08);border-color:rgba(63,185,106,.3)}

  .out{position:relative;border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin-top:12px;background:var(--panel2)}
  .out::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--wine),var(--rose),var(--gold))}
  .out-h{display:flex;align-items:center;justify-content:space-between;padding:12px 14px 8px;gap:8px;flex-wrap:wrap}
  .out-h .ttl{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--gold);font-weight:800}
  .copy{background:#0a0e15;border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:7px 12px;font-size:12px;cursor:pointer;font-family:inherit}
  .copy.done{border-color:var(--ok);color:var(--ok)}
  pre{margin:0;padding:0 14px 14px;white-space:pre-wrap;word-break:break-word;font-size:13.5px;color:#dde3ee;
    font-family:ui-monospace,Menlo,Consolas,monospace;line-height:1.65}
  pre .ph{color:var(--warn)} pre .hd{color:var(--rose);font-weight:700}

  table{width:100%;border-collapse:collapse;font-size:12.5px}
  td,th{padding:6px 8px;border-top:1px solid var(--line);vertical-align:top;color:#c4cce0;text-align:left}
  th{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.5px;border-top:0}
  td:first-child{color:var(--rose)}
  details summary{cursor:pointer;color:var(--sky);font-size:12.5px;font-weight:700;padding:4px 0}
  .foot{color:#5a6276;font-size:11px;text-align:center;margin-top:18px}
</style>
</head>
<body>

<div class="head">
  <div class="badge disp">KF2</div>
  <div class="t">KF2 Studio<small>Kroniki Fallathanu &middot; wiki, sesje i listingi WorkShop3D w jednym miejscu</small></div>
</div>

<nav class="tabs">
  <a href="{{ route('wiki.index') }}" class="{{ request()->routeIs('wiki.*') ? 'on' : '' }}">Wiki</a>
  <a href="{{ route('sesje.index') }}" class="{{ request()->routeIs('sesje.*') ? 'on' : '' }}">Sesje</a>
  <a href="{{ route('listingi.index') }}" class="{{ request()->routeIs('listingi.*') ? 'on' : '' }}">Listingi</a>
</nav>

@if (session('info'))
  <div class="note ok">{{ session('info') }}</div>
@endif

@if ($errors->any())
  <div class="note">
    @foreach ($errors->all() as $blad)
      {{ $blad }}<br>
    @endforeach
  </div>
@endif

@yield('tresc')

<div class="foot">KF2 Studio &middot; Kroniki Fallathanu (Thoran) &middot; WorkShop3D</div>

<script>
document.querySelectorAll("[data-kopiuj]").forEach(function (przycisk) {
  przycisk.addEventListener("click", function () {
    var zrodlo = document.getElementById(przycisk.dataset.kopiuj);
    var tekst = zrodlo.dataset.raw || zrodlo.textContent;
    var potwierdz = function () {
      przycisk.classList.add("done");
      var etykieta = przycisk.textContent;
      przycisk.textContent = "Skopiowano";
      setTimeout(function () {
        przycisk.classList.remove("done");
        przycisk.textContent = etykieta;
      }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(tekst).then(potwierdz, function () { zapasowe(tekst, potwierdz); });
    } else {
      zapasowe(tekst, potwierdz);
    }
  });
});

function zapasowe(tekst, gotowe) {
  var pole = document.createElement("textarea");
  pole.value = tekst;
  pole.style.position = "fixed";
  pole.style.opacity = "0";
  document.body.appendChild(pole);
  pole.select();
  try { document.execCommand("copy"); } catch (e) {}
  document.body.removeChild(pole);
  gotowe();
}
</script>
</body>
</html>
