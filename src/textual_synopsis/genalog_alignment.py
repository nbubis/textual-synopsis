from Bio import Align
from Bio.Align import substitution_matrices
from difflib import SequenceMatcher

MATCH_REWARD = 2
GAP_PENALTY = -0.5
GAP_EXT_PENALTY = -0.1
MISMATCH_PENALTY = -2.0
GAP_CHAR = "@"
ONE_ALIGNMENT_ONLY = False
SPACE_MISMATCH_PENALTY = 0.1  # Not fully supported in PairwiseAligner approximation


def _get_bigrams(w):
    """Return bigrams for a word, or the word itself if too short."""
    return set(w[i:i+2] for i in range(len(w)-1)) if len(w) > 1 else {w}

def _build_substitution_matrix(gt_tokens, noise_tokens, match_score, mismatch_score):
    """Build a dynamic substitution matrix for fuzzy word matching."""
    # Alphabet needs to contain all unique tokens. Bio.Align requires a tuple.
    # Add a dummy gap char to alphabet if not present (not strictly needed but safe)
    vocab1 = list(set(gt_tokens))
    vocab2 = list(set(noise_tokens))
    alphabet = tuple(set(vocab1 + vocab2))
    
    # Initialize with mismatch score
    m = substitution_matrices.Array(alphabet=alphabet, dims=2)
    m.fill(mismatch_score)
    
    # Precompute bigrams for vocab2 for speed
    v2_bigrams = [_get_bigrams(w) for w in vocab2]
    
    # Diagonal is match_score
    for w in alphabet:
        m[w, w] = match_score

    # Compute fuzzy overlap for pairs between the two sequences
    for w1 in vocab1:
        if len(w1) == 0:
            continue
        b1 = _get_bigrams(w1)
        for j, w2 in enumerate(vocab2):
            if w1 == w2 or len(w2) == 0:
                continue
            
            # Length difference heuristic
            if abs(len(w1) - len(w2)) > 2:
                continue
                
            # Must share at least one bigram (or unigram if very short)
            if not b1.intersection(v2_bigrams[j]):
                continue
                
            r = SequenceMatcher(None, w1, w2).ratio()
            # If highly similar (e.g. >= 0.40), give it a positive score slightly below match
            if r >= 0.40:
                # Scale r from [0.40, 1.0] to [0.0, match_score]
                fuzzy_score = (r - 0.40) / 0.60 * match_score
                # Ensure it's better than a gap or mismatch
                m[w1, w2] = max(mismatch_score / 2, fuzzy_score * 0.9)

    return m

def _align_seg(
    gt,
    noise,
    match_reward=MATCH_REWARD,
    mismatch_pen=MISMATCH_PENALTY,
    gap_pen=GAP_PENALTY,
    gap_ext_pen=GAP_EXT_PENALTY,
    space_mismatch_penalty=SPACE_MISMATCH_PENALTY,
    gap_char=GAP_CHAR,
    one_alignment_only=ONE_ALIGNMENT_ONLY,
):
    aligner = Align.PairwiseAligner()
    aligner.mode = "global"  # Global alignment
    
    # Use fuzzy word matching matrix instead of rigid match/mismatch scores
    try:
        sub_matrix = _build_substitution_matrix(gt, noise, match_reward, mismatch_pen)
        aligner.substitution_matrix = sub_matrix
    except Exception:
        # Fallback to simple matching if matrix creation fails
        aligner.match_score = match_reward
        aligner.mismatch_score = mismatch_pen
        
    aligner.open_gap_score = gap_pen
    aligner.extend_gap_score = gap_ext_pen

    try:
        aln = next(iter(aligner.align(gt, noise)))
    except StopIteration:
        return []

    # Bio.Align uses None for gaps in list/sequence alignments
    aligned_gt = [gap_char if x is None else x for x in aln[0]]
    aligned_noise = [gap_char if x is None else x for x in aln[1]]

    score = aln.score
    start = 0
    end = len(aligned_gt)

    results = []

    results.append((aligned_gt, aligned_noise, score, start, end))
    return results


def _select_alignment_candidates(alignments, target_num_gt_tokens):
    # Since we are already passing tokens, we just check lengths
    for alignment in alignments:
        aligned_gt = alignment[0]
        aligned_noise = alignment[1]
        
        # Count non-gap tokens
        num_aligned_gt_tokens = sum(1 for t in aligned_gt if t != GAP_CHAR)
        
        if num_aligned_gt_tokens == target_num_gt_tokens:
            if len(aligned_gt) != len(aligned_noise):
                raise ValueError(
                    "Aligned token lists are not equal in length"
                )
            return alignment

    raise ValueError(
        f"No alignment candidates with {target_num_gt_tokens} tokens. Total candidates: {len(alignments)}"
    )


def align(gt, noise, gap_char=GAP_CHAR):
    if not gt and not noise:
        return [], []
    elif not gt:
        return [gap_char] * len(noise), noise.copy()
    elif not noise:
        return gt.copy(), [gap_char] * len(gt)
    else:
        num_gt_tokens = len(gt)
        alignments = _align_seg(gt, noise, gap_char=gap_char)
        try:
            aligned_gt, aligned_noise, _, _, _ = _select_alignment_candidates(
                alignments, num_gt_tokens
            )
        except ValueError as e:
            # Fallback
            if alignments:
                return alignments[0][0], alignments[0][1]
            raise ValueError(
                f"Error with input tokens: \n{str(e)}"
            )
        return aligned_gt, aligned_noise
