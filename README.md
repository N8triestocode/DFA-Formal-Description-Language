# DFA-Formal-Description-Language
School Assignment using PLY and other components
Done by:
Nathan Bowen 2306494
Scott Spence 2100755
Joshaun Gibson 2210196 

## Requirements

Python 3.10 to 3.13 (3.12 recommended). Tick **Add python.exe to PATH** when installing.

## Running the project

```
git clone https://github.com/N8triestocode/DFA-Formal-Description-Language.git
cd DFA-Formal-Description-Language
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**No Git?** Click **Code → Download ZIP** on GitHub, unzip it, and open the **inner** folder that contains `app.py` (zips often nest a folder inside a folder of the same name). Then run the last two commands.

 The `python -m` form is used because `pip` and `streamlit` are often not on PATH on Windows.

Tests: `python -m unittest discover -v`