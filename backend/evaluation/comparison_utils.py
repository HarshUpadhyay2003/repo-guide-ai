import logging
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

def calculate_precision_recall_f1(predicted: Set[str], actual: Set[str]) -> Tuple[float, float, float]:
    """Calculate Precision, Recall, and F1 Score for two sets of strings."""
    if not predicted:
        precision = 0.0
    else:
        precision = len(predicted.intersection(actual)) / len(predicted)

    if not actual:
        recall = 0.0
    else:
        recall = len(predicted.intersection(actual)) / len(actual)

    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    return precision, recall, f1

def compare_paths(predicted_paths: List[str], actual_paths: List[str]) -> Dict[str, Any]:
    """Compare a list of predicted file/directory paths with actual paths."""
    pred_set = set(p.strip().replace("\\", "/").lower() for p in predicted_paths if p.strip())
    act_set = set(p.strip().replace("\\", "/").lower() for p in actual_paths if p.strip())

    precision, recall, f1 = calculate_precision_recall_f1(pred_set, act_set)

    matched = sorted(list(pred_set.intersection(act_set)))
    missed = sorted(list(act_set - pred_set))
    extra = sorted(list(pred_set - act_set))

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched": matched,
        "missed": missed,
        "extra": extra
    }

def infer_actual_difficulty(files_changed_count: int, commits_count: int) -> str:
    """Infer the actual difficulty level of a pull request based on size/effort signals."""
    if files_changed_count <= 2 and commits_count <= 2:
        return "Beginner"
    elif files_changed_count <= 5 and commits_count <= 5:
        return "Intermediate"
    else:
        return "Advanced"

def compare_issue_predictions(
    predicted_files: List[str],
    actual_files: List[str],
    predicted_dirs: List[str],
    actual_dirs: List[str],
    predicted_techs: List[str],
    actual_techs: List[str],
    predicted_difficulty: str,
    actual_difficulty: str,
    confidence_score: float
) -> Dict[str, Any]:
    """Calculate overlap stats and match details for an issue prediction vs ground truth."""
    file_cmp = compare_paths(predicted_files, actual_files)
    dir_cmp = compare_paths(predicted_dirs, actual_dirs)

    # Calculate overall match % (Average of File Recall and Directory Recall)
    # If there are no actual changes, match % is 0.0
    if not actual_files and not actual_dirs:
        overall_match = 0.0
        status = "No actual PR changes to evaluate"
    else:
        weights = []
        if actual_files:
            weights.append(file_cmp["recall"])
        if actual_dirs:
            weights.append(dir_cmp["recall"])
        overall_match = (sum(weights) / len(weights)) * 100.0 if weights else 0.0
        status = "Evaluated against merged PR"

    # Technologies overlap
    pred_tech_set = set(t.strip().lower() for t in predicted_techs if t.strip())
    act_tech_set = set(t.strip().lower() for t in actual_techs if t.strip())
    tech_matched = sorted(list(pred_tech_set.intersection(act_tech_set)))
    tech_match_ratio = len(tech_matched) / len(act_tech_set) if act_tech_set else 1.0

    # Difficulty match
    difficulty_match = predicted_difficulty.strip().lower() == actual_difficulty.strip().lower()

    return {
        "status": status,
        "files": file_cmp,
        "directories": dir_cmp,
        "overall_match_pct": overall_match,
        "tech_matched": tech_matched,
        "tech_match_ratio": tech_match_ratio,
        "difficulty_match": difficulty_match,
        "predicted_difficulty": predicted_difficulty,
        "actual_difficulty": actual_difficulty,
        "confidence_score": confidence_score
    }
