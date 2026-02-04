import re

from Bio import Align

from .genalog_preprocess import _is_spacing, tokenize

MATCH_REWARD = 1
GAP_PENALTY = -0.5
GAP_EXT_PENALTY = -0.1
MISMATCH_PENALTY = -2.0
GAP_CHAR = "@"
ONE_ALIGNMENT_ONLY = False
SPACE_MISMATCH_PENALTY = 0.1  # Not fully supported in PairwiseAligner approximation


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
    """Wrapper function for Bio.Align.PairwiseAligner, which
    calls the sequence alignment algorithm (Needleman-Wunsch)

    Arguments:
        gt (str) : a ground truth string
        noise (str) : a string with ocr noise
        match_reward (int, optional) : reward for matching characters. Defaults to ``MATCH_REWARD``.
        mismatch_pen (int, optional) : penalty for mistmatching characters. Defaults to ``MISMATCH_PENALTY``.
        gap_pen      (int, optional) : penalty for creating a gap. Defaults to ``GAP_PENALTY``.
        gap_ext_pen  (int, optional) : penalty for extending a gap. Defaults to ``GAP_EXT_PENALTY``.

    Returns:
        list : a list of alignment tuples. Each alignment tuple
        is one possible alignment candidate.

        A tuple (str, str, int, int, int) contains the following information:
            (aligned_gt, aligned_noise, alignment_score, alignment_start, alignment_end)
    """

    aligner = Align.PairwiseAligner()
    aligner.mode = "global"  # Global alignment
    aligner.match_score = match_reward
    aligner.mismatch_score = mismatch_pen
    # Bio.Align uses negative scores for penalties, but calls them scores.
    # Genalog defaults are negative (-0.5).
    aligner.open_gap_score = gap_pen
    aligner.extend_gap_score = gap_ext_pen

    # Helper to replace gap char
    def fix_gaps(s):
        return s.replace("-", gap_char)

    # print(f"DEBUG: Calling Bio.Align on {len(gt)} x {len(noise)} chars")

    # alignments = aligner.align(gt, noise)
    # Using format() might be safer/fast than coordinate reconstruction
    # But wait, format() produces huge strings for huge sequences?
    # Segments are small (100 chars).

    # Let's try to just get the first alignment
    try:
        aln = next(iter(aligner.align(gt, noise)))
    except StopIteration:
        return []

    # Extract strings using format() which gives:
    # TargetSeq
    # | | | |
    # QuerySeq
    # We take line 0 and line 2.
    # Note: Query/Target might depend on order.
    # align(target, query) -> gt is target, noise is query.

    lines = format(aln).split("\n")
    # format(aln) usually returns 3 lines.
    # But if there are gaps?
    # Bio.Align 1.80+ format:
    # "A-B\n|||\nACB"

    if len(lines) >= 3:
        aligned_gt = fix_gaps(lines[0])
        aligned_noise = fix_gaps(lines[2])
    else:
        # Fallback
        aligned_gt = fix_gaps(aln[0])
        aligned_noise = fix_gaps(aln[1])

    score = aln.score
    start = 0
    end = len(aligned_gt)

    results = []

    results.append((aligned_gt, aligned_noise, score, start, end))
    return results


def _select_alignment_candidates(alignments, target_num_gt_tokens):
    """Return an alignment that contains the desired number
    of ground truth tokens from a list of possible alignments

    Arguments:
        alignments (list) : a list of alignment tuples
        target_num_gt_tokens (int) : the number of token in the aligned ground truth string should have

    Returns:
        an alignment tuple (str, str, int, int, int)
    """
    for alignment in alignments:
        aligned_gt = alignment[0]
        aligned_noise = alignment[1]
        num_aligned_gt_tokens = len(tokenize(aligned_gt))
        # Invariant 2
        if num_aligned_gt_tokens == target_num_gt_tokens:
            # Invariant 1
            if len(aligned_gt) != len(aligned_noise):
                raise ValueError(
                    f"Aligned strings are not equal in length: \naligned_gt: '{aligned_gt}'\naligned_noise '{aligned_noise}'\n"
                )
            # Returns the FIRST candidate that satisfies the invariant
            return alignment

    raise ValueError(
        f"No alignment candidates with {target_num_gt_tokens} tokens. Total candidates: {len(alignments)}"
    )


def align(gt, noise, gap_char=GAP_CHAR):
    """Align two text segments via sequence alignment algorithm

    Arguments:
        gt (str) : ground true text (should not contain GAP_CHAR)
        noise (str) : str with ocr noise (should not contain GAP_CHAR)
        gap_char (char, optional) : gap char used in alignment algorithm (default: GAP_CHAR)

    Returns:
        tuple(str, str) : a tuple of aligned ground truth and noise
    """
    if not gt and not noise:  # Both inputs are empty string
        return "", ""
    elif not gt:  # Either is empty
        return gap_char * len(noise), noise
    elif not noise:
        return gt, gap_char * len(gt)
    else:
        num_gt_tokens = len(tokenize(gt))
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
                f"Error with input strings '{gt}' and '{noise}': \n{str(e)}"
            )
        return aligned_gt, aligned_noise
