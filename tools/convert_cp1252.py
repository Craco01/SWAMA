# Decodifica un archivo en bytes interpretándolos como CP1252 y guarda en UTF-8
from pathlib import Path
p = Path('MSJ AUTO/mensajes_first_raw.py')
out = Path('MSJ AUTO/mensajes_first_cp1252_to_utf8.py')
raw = p.read_bytes()
text = raw.decode('cp1252')
out.write_text(text, encoding='utf-8')
print('ok')
