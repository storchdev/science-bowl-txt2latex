# SCIENCE BOWL TXT 2 LATEX CONVERTER

## description
converts your ugly Google Doc written questions into professional DoE style

## instructions
- create a `in.txt` (example format in `example_in.txt`, it is quite flexible)
- run `main.py --help` and figure out how to get the .tex files you need
- copy the .tex to a LaTeX compiler that supports Times New Roman (e.g. XeLaTeX) on a website like https://overleaf.com

## notes
- you must run with `--compmode` at this time
- by default, mcq choices are shuffled + answer choices and answers are lowercase
  - add ~ before an answer choice or answer to keep it as is
  - add the `-nac` tag on the first line of the question to keep all answer choices and answers as is
  - add the `-ns` tag on the first line of the question to not shuffle choices
- specify difficulty on the first line of the question with `xd` where `x` could be `1d`, `10d`, `8.8d`
  - this is for the automatic tossup/bonus pairing and round division algorithms
  - there is no limit for the numbers, but you can specify
- ignore the ID= stuff in the example_in.txt
- will runtime error if your in.txt doesn't adhere to the format (it can be picky)
- might generate fewer rounds than expected due to randomness of the pairing algorithm
  - just play with the seed if this happens for now