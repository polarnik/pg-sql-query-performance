#!/bin/bash -x


#/c/Tools/marp/marp.exe --output "$(pwd)/slides.pdf" --allow-local-files --pdf --theme "$(pwd)/themes/vtb.css" -I "$(pwd)"

#/c/Tools/marp/marp.exe --output "$(pwd)/slides.pptx" --allow-local-files --pptx --theme "$(pwd)/themes/vtb.css" -I "$(pwd)"

# /c/Tools/marp/marp.exe --output "$(pwd)" --watch --allow-local-files --html --theme "$(pwd)/themes/vtb.css" --template "bare" --bespoke.osc false --bespoke.progress false -I "$(pwd)"

/c/Tools/marp/marp.exe --output "$(pwd)" --watch --allow-local-files  --html --template "bespoke" --bespoke.osc true --bespoke.progress true  -I "$(pwd)"