from pathlib import Path
encodings = ['utf-8','utf-16','utf-16-le','utf-16-be','cp1252','latin1','cp437']
raw_path = Path('MSJ AUTO/mensajes_first_raw.py')
out_dir = Path('MSJ AUTO')
raw = raw_path.read_bytes()
best = None
best_score = -1
for enc in encodings:
    try:
        s = raw.decode(enc)
    except Exception:
        continue
    score = sum(s.count(ch) for ch in 'áéíóúñÁÉÍÓÚÑ')
    if score>best_score:
        best_score = score
        best = (enc,s)
print('best encoding:', best[0], 'score', best_score)
out_path = out_dir / 'mensajes_first_autodetected.py'
out_path.write_text(best[1], encoding='utf-8')
print('wrote', out_path)
