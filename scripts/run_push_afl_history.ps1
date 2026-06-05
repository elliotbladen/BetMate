$env:BETMATE_ROOT = "C:\Users\ElliotBladen\Apps"
$env:PYTHONUTF8  = "1"

& C:\Users\ElliotBladen\.local\bin\uv.exe run --with requests --with openpyxl python "$env:BETMATE_ROOT\scripts\push_afl_history.py"
