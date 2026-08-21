from ftfy import fix_text
from pathlib import Path
p = Path('MSJ AUTO/mensajes_first_autodetected.py')
s = p.read_text(encoding='utf-8')
fixed = fix_text(s)
out = Path('MSJ AUTO/mensajes_first_fixed.py')
out.write_text(fixed, encoding='utf-8')
print('wrote', out)
