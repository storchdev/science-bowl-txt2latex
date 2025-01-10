import re 
import argparse
import os
from typing import List, Optional
from textwrap import dedent
import logging
import platform


parser = argparse.ArgumentParser()
parser.add_argument("--round", "-r", help="what round these questions should be part of", type=int, required=False)
parser.add_argument("--input", "-i", help="name of the input file", type=str, default="in.txt")
parser.add_argument("--output", "-o", help="name of the output file", type=str, default="out.tex")
parser.add_argument("--clipboard", "-c", help="whether or not to copy output to clipboard", action="store_true")
parser.add_argument("--no-bonus", "-nb", help="whether or not to do pure tossups", action="store_true")

args = parser.parse_args()
if args.round:
    ROUND = args.round
else:
    ROUND = 1


prelude = r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\usepackage{unicode-math}
\setmathfont{TeX Gyre Termes Math}
\usepackage{setspace}

\hyphenpenalty=10000
\exhyphenpenalty=10000

\begin{document}
\onehalfspacing
\raggedright
\setlength{\parindent}{0pt}
\centerline{\textbf{2025 EQUITY NORTH-EAST SCIENCE BOWL}}
\bigskip
\centerline{\textbf{ROUND [round]}}
\bigskip


% Questions begin here
""".replace('[round]', str(ROUND))

postlude = r"""


\end{document}
"""


class Question:
    g_q_number = 1
    g_is_tossup = True

    def __init__(self,
                 subject: str,
                 is_mcq: bool,
                 q_text: str,
                 a_text: str,
                 q_choices: Optional[List[str]],
                 a_letter: Optional[str],
                 difficulty: int
                 ):

        self.subject = subject
        self.is_mcq = is_mcq
        self.q_text = q_text
        self.a_text = a_text
        self.q_choices = q_choices
        self.a_letter = a_letter
        self.difficulty = difficulty

    @classmethod
    def from_raw(cls, raw_question: str):
        raw_lines = raw_question.split('\n')

        if len(raw_lines) < 3:
            raise RuntimeError(f"Too few lines in raw question:\n{raw_question}")

        tokens1 = raw_lines[0].split()

        if len(tokens1) == 3:
            m = re.match(r'(\d)*', tokens1[2])
            if not m:
                raise RuntimeError(f'Incorrect difficulty in raw question:\n{raw_question}')
            
            difficulty = int(m.group(1))
        elif len(tokens1) == 2:
            raw_subject = tokens1[0]
            raw_mcqsaq = tokens1[1]
            difficulty = None
        else:
            raise RuntimeError(f"Incorrect number of tokens1\nLine: {raw_lines[0]}")
        
        raw_subject = raw_subject.lower()
        raw_mcqsaq = raw_mcqsaq.lower()

        if raw_subject in ('bio', 'biology'):
            subject = 'bio'
        elif raw_subject in ('phys', 'physics'):
            subject = 'phys'
        elif raw_subject in ('math'):
            subject = 'math'
        elif raw_subject in ('chem', 'chemistry'):
            subject = 'chem'
        elif raw_subject in ('ess', 'earth'):
            subject = 'ess'
        else:
            raise RuntimeError(f"Unrecognized subject\nLine: {raw_lines[0]}")
        
        if raw_mcqsaq in ('mcq', 'mc', 'm'):
            is_mcq = True
        elif raw_mcqsaq in ('saq', 'sa', 's'):
            is_mcq = False
        else:
            raise RuntimeError(f"Unrecognized mcq/saq\nLine: {raw_lines[0]}")
        
        q_text = raw_lines[1]
        if not q_text[0].isupper():
            logging.warning(f"{q_text} does not begin with a capital letter")
        if q_text[-1] != '?':
            logging.warning(f"{q_text} does not end with a question mark")

        if is_mcq:
            if len(raw_lines) != 7:
                raise RuntimeError(f"Incorrect number of lines in mcq:\n{raw_question}")
            q_choices = []
            for char, line in zip('wxyz', raw_lines[2:6]):
                m = re.match(r'^([wxyz]) (.+?)$', line, re.IGNORECASE)
                if m:
                    if m.group(1).lower() == char:
                        line = m.group(2)
                    else:
                        logging.warning(f"Choice {line} might be incorrectly lettered in \"{q_text}\"")

                if line.startswith('~'):
                    line = line.removeprefix('~')
                elif any(c.isupper() for c in line):
                    line = line.lower()
                    logging.warning(f"Lowercasifying choice \"{line}\"")
                
                q_choices.append(line)
            
            a_line = raw_lines[6]
            m = re.match(r'^([wxyz]) (.+?)$', a_line.lower())
            if not m:
                raise RuntimeError(f"Missing answer letter in mcq: {q_text}")
            
            a_line = m.group(2)
            a_letter = m.group(1).upper()

        else:
            if len(raw_lines) != 3:
                raise RuntimeError(f"Incorrect number of lines in saq:\n{raw_question}")

            q_choices = None
            a_line = raw_lines[2]
            a_letter = None

        if a_line.startswith('~'):
            a_line = a_line.removeprefix('~')
        elif any(c.isupper() for c in a_line):
            a_line = a_line.lower()
            logging.warning(f"Lowercasifying answer \"{a_line}\"")

        a_text = a_line

        return cls(
            subject,
            is_mcq,
            q_text,
            a_text,
            q_choices,
            a_letter,
            difficulty
        )

    def to_latex(self):
        if self.is_mcq:
            return self.to_latex_mcq()
        else:
            return self.to_latex_saq()

    def to_latex_mcq(self):
        if Question.g_is_tossup:
            tb = 'TOSS-UP'
            if not args.no_bonus:
                Question.g_is_tossup = False
        else:
            tb = 'BONUS'
            Question.g_is_tossup = True

        full_subjects = {
            "bio": "Biology",
            "ess": "Earth and Space",
            "math": "Math",
            "chem": "Chemistry",
            "phys": "Physics"
        }

        latex = r"""
            \begin{minipage}{\textwidth}
            \bigskip\hrule\bigskip
            \centerline{\textbf{[tb]}}
            [#]) [subject] – \textit{Multiple Choice}\quad [qtext]\\~\\
            W) [w]\\
            X) [x]\\
            Y) [y]\\
            Z) [z]\\~\\
            ANSWER: [aletter]) [atext]
            \end{minipage}
        """
        latex = latex.replace('[#]', str(Question.g_q_number))
        latex = latex.replace('[tb]', tb)
        latex = latex.replace('[subject]', full_subjects[self.subject])
        latex = latex.replace('[qtext]', self.q_text)

        for letter, choice in zip('wxyz', self.q_choices):
            latex = latex.replace(f'[{letter}]', choice)
        
        latex = latex.replace('[aletter]', self.a_letter)
        latex = latex.replace('[atext]', self.a_text)

        Question.g_q_number += 1

        return dedent(latex).strip('\n')

    def to_latex_saq(self):
        if Question.g_is_tossup:
            tb = 'TOSS-UP'
            if not args.no_bonus:
                Question.g_is_tossup = False
        else:
            Question.g_is_tossup = True
            tb = 'BONUS'

        full_subjects = {
            "bio": "Biology",
            "ess": "Earth and Space",
            "math": "Math",
            "chem": "Chemistry",
            "phys": "Physics"
        }

        latex = r"""
            \begin{minipage}{\textwidth}
            \bigskip\hrule\bigskip
            \centerline{\textbf{[tb]}}
            [#]) [subject] – \textit{Short Answer}\quad [qtext]\\~\\
            ANSWER: [atext]
            \end{minipage}
        """
        latex = latex.replace('[#]', str(Question.g_q_number))
        latex = latex.replace('[tb]', tb)
        latex = latex.replace('[subject]', full_subjects[self.subject])
        latex = latex.replace('[qtext]', self.q_text)

        latex = latex.replace('[atext]', self.a_text)

        Question.g_q_number += 1

        return dedent(latex).strip('\n')


with open(args.input) as f:
    raw_text = f.read().strip('\n')

raw_questions = re.split(r"\n\n+", raw_text)
# raw_questions = raw_questions[-1:]

qlist: List[Question] = []
for raw_q in raw_questions:
    qlist.append(Question.from_raw(raw_q))


# DIFFICULTY HANDLING/REORDERING SHOULD BE DONE HERE


latexlist: List[str] = []
for q in qlist:
    latexlist.append(q.to_latex())

body = '\n\n'.join(latexlist)

with open(args.output, 'w') as f:
    f.write(prelude + body + postlude)
    print(f"Saved output to {args.output}")

if args.clipboard:
    if platform.system() == "Mac":
        os.system(f"cat {args.output} | pbcopy")
    elif platform.system() == "Linux":
        os.system(f"cat {args.output} | xclip -selection clipboard")
    
    print("Copied output to clipboard")

