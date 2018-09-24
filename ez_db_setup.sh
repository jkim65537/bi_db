#!/bin/bash

if [[ "$OSTYPE" == "linux-gnu" ]]; then
    python_local="/home/$USER/.local/lib/python2.7/site-packages"
    bi_db_path="/home/$USER/bi_db"
    cd "/home/$USER"
elif [[ "$OSTYPE" == "msys" ]]; then
    python_local="C:/Users/$USERNAME/AppData/Local/Continuum/anaconda2/Lib/site-packages"
    bi_db_path="C:/Users/$USERNAME/bi_db"
    cd "C:/Users/$USERNAME"
fi

if [ -d "$python_local/bi_db" ]; then
  mkdir -p "$python_local/bi_db"
fi

cp "$bi_db_path/biz_intel_creds.py" "$python_local/biz_intel_creds.py"
cp -TRv "$bi_db_path" "$python_local/bi_db"

echo "bi_db installation is complete"
