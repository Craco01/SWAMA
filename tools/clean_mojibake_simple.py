from pathlib import Path
p = Path('MSJ AUTO/mensajes_first_fixed.py')
s = p.read_text(encoding='utf-8')
replacements = {
    '├¡':'í',
    '├©':'é',
    '├®':'é',
    '├▒':'ñ',
    '├│':'ó',
    '├║':'ú',
    '├í':'á',
    'ÔÇó':'•',
    '┬í':'¡',
    '┬º':'º',
    '┐':'',
}
for k,v in replacements.items():
    s = s.replace(k,v)
out = Path('MSJ AUTO/mensajes_first_clean.py')
out.write_text(s, encoding='utf-8')
print('wrote', out)
