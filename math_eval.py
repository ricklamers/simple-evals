"""
Measuring Mathematical Problem Solving With the MATH Dataset
Dan Hendrycks, Collin Burns, Saurav Kadavath, Akul Arora, Steven Basart, Eric Tang, Dawn Song, Jacob Steinhardt
https://arxiv.org/abs/2103.03874
"""

import random
import re

import blobfile as bf
import pandas

try:
    import common
    from common import ANSWER_PATTERN, HTML_JINJA, check_equality
    from type_definitions import Eval, EvalResult, SamplerBase, SingleEvalResult
except:
    from . import common
    from .common import ANSWER_PATTERN, HTML_JINJA, check_equality
    from .type_definitions import Eval, EvalResult, SamplerBase, SingleEvalResult

QUERY_TEMPLATE = """{Question}. The last line of your response should be of the form Answer: $ANSWER (without quotes) where $ANSWER is the answer to the problem. """


class MathEval(Eval):
    def __init__(self, equality_checker: SamplerBase, num_examples: int | None = None):
        df = pandas.read_csv(
            "https://openaipublic.blob.core.windows.net/simple-evals/math_test.csv"
        )
        examples = [row.to_dict() for _, row in df.iterrows()]
        if num_examples:
            examples = random.Random(0).sample(examples, num_examples)
        self.examples = examples
        self.equality_checker = equality_checker

    def __call__(self, sampler: SamplerBase) -> EvalResult:
        def fn(row: dict):
            prompt_messages = [
                sampler._pack_message(content=QUERY_TEMPLATE.format(**row), role="user")
            ]
            response_text = sampler(prompt_messages)
            match = re.search(ANSWER_PATTERN, response_text)
            extracted_answer = match.group(1) if match else None
            score = float(check_equality(self.equality_checker, row["Answer"], extracted_answer))
            #print(f"Extracted answer: {extracted_answer}, Correct answer: {row['Answer']}, Score: {score}")
            html = common.jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=prompt_messages,
                next_message=dict(content=response_text, role="assistant"),
                score=score,
                correct_answer=row["Answer"],
                extracted_answer=extracted_answer,
            )
            convo = prompt_messages + [dict(content=response_text, role="assistant")]
            return SingleEvalResult(html=html, score=score, convo=convo)

        results = common.map_with_progress(fn, self.examples)
        return common.aggregate_results(results)
