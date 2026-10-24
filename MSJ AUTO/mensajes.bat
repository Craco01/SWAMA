@echo off
cd /d "C:\Users\Christian Redes\OneDrive - Grupo MV\Escritorio\Reportes WA con Selenium\MSJ AUTO"
"C:\Users\Christian Redes\AppData\Local\Programs\Python\Python313\python.exe" "mensajes.py" %1 >> "mensajes_salida.txt" 2>&1
