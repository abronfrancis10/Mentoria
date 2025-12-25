def calculate_final_score(answer_score: float, voice_score: float):
    final_score = (0.7 * answer_score) + (0.3 * voice_score)

    feedback = []

    if final_score >= 8:
        feedback.append("Excellent overall performance.")
    elif final_score >= 6:
        feedback.append("Good performance, minor improvements needed.")
    elif final_score >= 4:
        feedback.append("Average performance, needs improvement.")
    else:
        feedback.append("Poor performance, significant improvement required.")

    return {
        "final_score": round(final_score, 2),
        "overall_feedback": feedback
    }
