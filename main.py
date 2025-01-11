import re 
import argparse
import os
from typing import List, Optional
from textwrap import dedent
import logging
import platform
import random 
from collections import defaultdict, Counter


random.seed(611)
# random.seed(1)

parser = argparse.ArgumentParser()
parser.add_argument("--round", "-r", help="what round these questions should be part of. does not apply when using --realshit", type=int, required=False)
parser.add_argument("--round-name", "-rn", help="name of round, will appear on document. does not apply when using --realshit", type=int, required=False)
parser.add_argument("--input", "-i", help="name of the input file", type=str, default="in.txt")
parser.add_argument("--output", "-o", help="name of the output file. does not apply when using --realshit", type=str, default="out.txt")
parser.add_argument("--no-bonus", "-nb", help="whether or not to do pure tossups. does not apply when using --realshit", action="store_true")
parser.add_argument("--realshit", "-rs", help="whether or not to do EVERYTHING (for a real contest)", action="store_true")

args = parser.parse_args()
if args.round:
    ROUND = args.round
else:
    ROUND = 1

if args.round_name:
    round_name = args.round_name
else:
    round_name = str(ROUND)


prelude = r"""\documentclass[10pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\usepackage{unicode-math}
\setmathfont{TeX Gyre Termes Math}
\usepackage{setspace}
\usepackage{mhchem}

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
"""

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

    def __eq__(self, other):
        return self.q_text == other.q_text

    @classmethod
    def from_raw(cls, raw_question: str):
        raw_lines = raw_question.split('\n')

        if len(raw_lines) < 3:
            raise RuntimeError(f"Too few lines in raw question:\n{raw_question}")

        tokens1 = raw_lines[0].split()

        if len(tokens1) >= 2:
            raw_subject = tokens1[0]
            raw_mcqsaq = tokens1[1]
        else:
            raise RuntimeError(f"Incorrect number of tokens1in line: \"{raw_lines[0]}\"")

        if '-nac' in tokens1:
            auto_capitalize = False
        else:
            auto_capitalize = True

        if '-ns' in tokens1:
            shuffle = False
        else:
            shuffle = True
        
        difficulty = None
        for t in tokens1:
            if t.endswith('d'):
                try:
                    difficulty = int(t[0])
                except ValueError:
                    continue
                break
        
        if difficulty is None:
            raise RuntimeError(f"Question has no difficulty:\n{raw_question}")
        
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
            logging.warning(f"Question does not begin with a capital letter: \"{q_text}\"")
        if q_text[-1] != '?':
            logging.warning(f"Question does not end with a question mark: \"{q_text}\"")

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
                elif any(c.isupper() for c in line) and auto_capitalize and r"\ce{" not in line:
                    line = line.lower()
                    logging.warning(f"Lowercasifying choice \"{line}\"")
                
                q_choices.append(line)
            
            a_line = raw_lines[6]
            m = re.match(r'^([wxyz]) (.+?)$', a_line, re.IGNORECASE)
            if not m:
                raise RuntimeError(f"Missing answer letter in mcq: {q_text}")
            
            a_line = m.group(2)
            a_letter = m.group(1).upper()

            # shuffle here
            if shuffle:
                a_tuples = [(char, choice) for char, choice in zip('WXYZ', q_choices)]
                random.shuffle(a_tuples)
                for char2, (char, choice) in zip('WXYZ', a_tuples):
                    if char == a_letter:
                        a_letter = char2
                        break
                
                q_choices = [t[1] for t in a_tuples]

        else:
            if len(raw_lines) != 3:
                raise RuntimeError(f"Incorrect number of lines in saq:\n{raw_question}")

            q_choices = None
            a_line = raw_lines[2]
            a_letter = None

        if a_line.startswith('~'):
            a_line = a_line.removeprefix('~')
        elif any(c.isupper() for c in a_line) and auto_capitalize and r"\ce{" not in a_line:
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
        else:
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
        latex = latex.replace('[d]', str(self.difficulty))

        for letter, choice in zip('wxyz', self.q_choices):
            latex = latex.replace(f'[{letter}]', choice)
        
        latex = latex.replace('[aletter]', self.a_letter)
        latex = latex.replace('[atext]', self.a_text)

        if args.no_bonus:
            Question.g_is_tossup = True
            Question.g_q_number += 1
        else:
            if not Question.g_is_tossup:
                Question.g_q_number += 1

            Question.g_is_tossup = not Question.g_is_tossup

        return dedent(latex).strip('\n')

    def to_latex_saq(self):
        if Question.g_is_tossup:
            tb = 'TOSS-UP'
        else:
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
        latex = latex.replace('[d]', str(self.difficulty))

        latex = latex.replace('[atext]', self.a_text)

        if args.no_bonus:
            Question.g_is_tossup = True
            Question.g_q_number += 1
        else:
            if not Question.g_is_tossup:
                Question.g_q_number += 1

            Question.g_is_tossup = not Question.g_is_tossup

        return dedent(latex).strip('\n')


with open(args.input) as f:
    raw_text = f.read().strip('\n')

raw_questions = re.split(r"\n\n+", raw_text)
# raw_questions = raw_questions[-1:]

qlist: List[Question] = []
for raw_q in raw_questions:
    qlist.append(Question.from_raw(raw_q))


# REALSHIT BEGINS

if args.realshit:

    for q in qlist:
        if q.difficulty is None:
            q.difficulty = random.uniform(0, 6)
        else:
            q.difficulty += random.uniform(-1, 1)

    def pair_questions(qlist):
        # Step 1: Group questions by subject
        subject_groups = defaultdict(list)

        for question in qlist:
            subject_groups[question.subject].append(question)
        
        # Step 2: Sort questions by difficulty within each subject group
        for subject in subject_groups:
            subject_groups[subject].sort(key=lambda q: q.difficulty)
        
        # Step 3: Create tossup-bonus pairs
        pairs = []
        for subject, questions in subject_groups.items():
            used = set()
            for i in range(len(questions)):
                if i in used:
                    continue  # Skip already paired questions
                for j in range(i + 1, len(questions)):
                    if j in used:
                        continue  # Skip already paired questions
                    if questions[j].difficulty >= questions[i].difficulty + 1:
                        # Found a valid tossup-bonus pair
                        pairs.append((questions[i], questions[j]))
                        used.add(i)
                        used.add(j)
                        break  # Move to the next tossup candidate

        return pairs

    qpairs = pair_questions(qlist)

    def divide_into_chunks(pairs):
        # Step 1: Group pairs by subject
        subject_groups = defaultdict(list)
        for tossup, bonus in pairs:
            subject_groups[tossup.subject].append((tossup, bonus))

        # Step 2: Sort each subject group by tossup difficulty
        for subject in subject_groups:
            subject_groups[subject].sort(key=lambda pair: pair[0].difficulty)
        
        # Step 3: Form chunks
        chunks = []
        while True:
            chunk = []
            complete_chunk = True
            for subject, pairs in subject_groups.items():
                if len(pairs) < 5:
                    complete_chunk = False
                    break
                # Add 5 pairs from this subject to the current chunk
                chunk.extend(pairs[:5])
                # Remove these pairs from the subject group
                subject_groups[subject] = pairs[5:]
            if complete_chunk:
                # print(len(chunk))
                chunks.append(chunk)
            else:
                break  # Stop if we can't form a complete chunk of 25 pairs

        return chunks

    qpairchunks = divide_into_chunks(qpairs)
    # print(len(qpairchunks))

    def shuffle_chunk(chunk):
        # Step 1: Group pairs by subject
        subject_groups = defaultdict(list)
        for pair in chunk:
            subject_groups[pair[0].subject].append(pair)

        # Step 2: Initialize variables
        shuffled_list = []
        last_subject = None

        # Step 3: Form groups of 5 distinct-subject pairs
        while any(subject_groups.values()):
            group = []
            available_subjects = set(subject_groups.keys())

            # Ensure no subject repetition within the group
            for _ in range(5):
                # Filter out subjects already in the group
                eligible_subjects = [subj for subj in available_subjects if subj not in [p[0].subject for p in group]]

                # If no eligible subjects are left, reset the group to avoid deadlock
                if not eligible_subjects:
                    break

                # Pick a subject, avoiding the last_subject
                eligible_subjects = [subj for subj in eligible_subjects if subj != last_subject]
                if not eligible_subjects:
                    # If no eligible subjects remain, fallback to all available subjects
                    eligible_subjects = [subj for subj in available_subjects if subj not in [p[0].subject for p in group]]

                chosen_subject = random.choice(eligible_subjects)
                group.append(subject_groups[chosen_subject].pop(0))
                last_subject = chosen_subject

                # Remove subject if it's empty
                if not subject_groups[chosen_subject]:
                    del subject_groups[chosen_subject]

            # Append the group to the shuffled list
            shuffled_list.extend(group)

            # Check boundary constraint
            if len(shuffled_list) > 5:
                prev_subject = shuffled_list[-6][0].subject
                curr_subject = shuffled_list[-5][0].subject
                if prev_subject == curr_subject:
                    # Swap within the group to avoid boundary violation
                    for i in range(len(group)):
                        if group[i][0].subject != prev_subject:
                            shuffled_list[-5], group[i] = group[i], shuffled_list[-5]
                            break

        return shuffled_list

    roundnum = 1
    og_list = qlist.copy()
    for qpairs in qpairchunks:
        Question.g_q_number = 1

        newqlist = shuffle_chunk(qpairs)

        latexlist: List[str] = []
        for q1, q2 in newqlist:
            # latexlist.append(q.to_latex())
            latexlist.append(q1.to_latex())
            latexlist.append(q2.to_latex())
            og_list.remove(q1)
            og_list.remove(q2)

        body = '\n\n'.join(latexlist)

        fname = f'out/round_{roundnum}.tex'

        with open(fname, 'w') as f:
            f.write(prelude.replace('[round]', str(roundnum)) + body + postlude)
            print(f"Saved output to {fname}")

        # if args.clipboard:
        #     if platform.system() == "Darwin":
        #         os.system(f"cat {args.output} | pbcopy")
        #     elif platform.system() == "Linux":
        #         os.system(f"cat {args.output} | xclip -selection clipboard")
            
        #     print("Copied output to clipboard")
        
        roundnum += 1


    print(len(og_list)) 
    Question.g_q_number = 1
    latexlist: List[str] = []

    for q in og_list:
        latexlist.append(q.to_latex())

    body = '\n\n'.join(latexlist)

    fname = f'out/round_extras.tex'

    with open(fname, 'w') as f:
        f.write(prelude.replace('[round]', str(roundnum)) + body + postlude)
        print(f"Saved output to {fname}")

    

print(len(raw_questions))
