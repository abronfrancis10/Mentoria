def evaluate_answer(answer: str):
    length_score = min(len(answer.split()) / 50, 1) * 10
    return round(length_score, 2)
