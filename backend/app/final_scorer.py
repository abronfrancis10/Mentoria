def calculate_final_score(optimality, answer_quality, voice):
    final = (
        0.5 * optimality +
        0.2 * answer_quality +
        0.3 * voice
    )

    if final >= 8:
        feedback = "Excellent performance"
    elif final >= 6:
        feedback = "Good, needs minor improvement"
    elif final >= 4:
        feedback = "Average, needs improvement"
    else:
        feedback = "Poor performance"

    return round(final, 2), feedback
