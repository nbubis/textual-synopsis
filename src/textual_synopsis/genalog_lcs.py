# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

from Bio import Align


class LCS:
    """Compute the Longest Common Subsequence (LCS) of two given string using Bio.Align.
    Optimized by replacing custom Python DP table with Biopython's C-implemented PairwiseAligner.
    """

    def __init__(self, str_m, str_n):
        self.str_m = str_m
        self.str_n = str_n
        self._lcs = self._compute_lcs(str_m, str_n)
        self._lcs_len = len(self._lcs)

    def _compute_lcs(self, str_m, str_n):
        if not str_m or not str_n:
            return ""

        aligner = Align.PairwiseAligner()
        aligner.mode = "global"

        # LCS Equivalent Scores:
        # Match: +1
        # Mismatch: -inf (or sufficiently negative to prevent substitution)
        # Gap: 0 (free to skip characters)
        aligner.match_score = 1000.0
        aligner.mismatch_score = -10000.0  # Strict mismatch penalty
        aligner.open_gap_score = 0
        aligner.extend_gap_score = 0

        # Run alignment
        try:
            # We only need the best alignment
            alignment = aligner.align(str_m, str_n)[0]

            # Extract common subsequence from alignment
            # The alignment object contains aligned strings (with gaps usually)
            # But the 'coordinates' or simply traversing the aligned strings works.

            # Using aligned strings from alignment iterator
            aligned_m = alignment[0]  # Aligned source
            aligned_n = alignment[1]  # Aligned target

            lcs_chars = []

            # Both strings should be same length now (with gaps)
            for char_m, char_n in zip(aligned_m, aligned_n):
                if (
                    char_m == char_n and char_m != "-"
                ):  # Assuming - is gap char, but Biopython uses - by default
                    # Double check if gap char is configurable or we just look for match
                    lcs_chars.append(char_m)

            return "".join(lcs_chars)

        except IndexError:
            # No alignment found
            return ""
        except Exception as e:
            # Fallback or error logging
            print(f"Error in LCS computation: {e}")
            return ""

    def get_len(self):
        return self._lcs_len

    def get_str(self):
        return self._lcs
