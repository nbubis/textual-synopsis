import os
import glob
from . import genalog_alignment
from .genalog_anchor import align_w_anchor
from .genalog_preprocess import tokenize, join_tokens


def load_texts_from_directory(directory_path):
    """
    Loads all text files from the directory.
    Returns a list of tuples: (filename, content), sorted by filename.
    """
    files = sorted(glob.glob(os.path.join(directory_path, "*")))
    texts = []
    # Filter for text files if needed, or just try to read all
    for f in files:
        if os.path.isfile(f):
            try:
                with open(f, "r", encoding="utf-8") as f_obj:
                    # Normalize text: tokenize and rejoin to ensure consistency with genalog alignment
                    # This removes newlines and extra spaces, preventing length mismatches in Star Alignment
                    raw_content = f_obj.read()
                    normalized_content = join_tokens(tokenize(raw_content))
                    texts.append((os.path.basename(f), normalized_content))
            except Exception as e:
                print(f"Skipping {f} due to error: {e}")
    return texts


class StarAligner:
    def __init__(self, texts_with_ids):
        """
        texts_with_ids: list of (id, text_content)
        """
        self.texts = texts_with_ids
        self.gap_char = genalog_alignment.GAP_CHAR

    def _select_pivot(self):
        """
        Selects the text with the maximum length as the pivot.
        Returns index of pivot in self.texts.
        """
        max_len = -1
        pivot_idx = -1
        for i, (tid, content) in enumerate(self.texts):
            if len(content) > max_len:
                max_len = len(content)
                pivot_idx = i
        return pivot_idx

    def align(self):
        if not self.texts:
            return []

        pivot_idx = self._select_pivot()
        pivot_id, pivot_content = self.texts[pivot_idx]

        # P: The actual characters of the pivot (without gaps)
        # We will iterate through P to anchor our MSA
        P = pivot_content

        # Data structures to hold alignment info relative to P
        # slots[k] holds insertions (strings) from other texts appearing BEFORE P[k]
        # slots[len(P)] holds insertions AFTER the last char of P
        # Each element of slots is a list of strings, one for each "other" text.

        other_indices = [i for i in range(len(self.texts)) if i != pivot_idx]
        # Map from original index to 'other' index (0..N-2) for storage in lists
        text_idx_map = {
            original_i: list_i for list_i, original_i in enumerate(other_indices)
        }

        num_others = len(other_indices)
        slots = [["" for _ in range(num_others)] for _ in range(len(P) + 1)]

        # matches[k] holds the character aligned to P[k] for each other text
        matches = [["" for _ in range(num_others)] for _ in range(len(P))]

        print(f"Selected pivot: {pivot_id} (Length: {len(P)})")

        for other_i in other_indices:
            other_id, other_content = self.texts[other_i]
            print(f"Aligning {other_id} against pivot...")

            # aligned_gt corresponds to Pivot (P) with gaps
            # aligned_noise corresponds to Other (T) with gaps
            # Use direct global alignment instead of anchored alignment.
            # Anchored alignment can cause block shifts if it latches onto false positive anchors (common words).
            # Since we optimized genalog_alignment to use Bio.Align (C-based), it can handle 10k+ chars efficiently.
            aligned_pivot, aligned_other = genalog_alignment.align(
                pivot_content, other_content
            )

            # Parse the alignment to fill slots and matches
            p_idx = 0  # Index in original P
            mapped_i = text_idx_map[other_i]

            current_insertion = []

            for char_p, char_t in zip(aligned_pivot, aligned_other):
                if char_p == self.gap_char:
                    # Gap in Pivot -> Insertion in Other (or Gap in Other matching Gap in Pivot? No, one must be char)
                    # Ideally char_t is not a gap if char_p is a gap (otherwise it's redundant gap)
                    # But pairwise2 might output double gaps? Typically not in optimal alignment.
                    current_insertion.append(char_t)
                else:
                    # char_p is a character from P. It must match P[p_idx]
                    # Verify sanity
                    # assert char_p == P[p_idx]

                    # Commit pending insertions to the slot BEFORE P[p_idx]
                    slots[p_idx][mapped_i] = "".join(current_insertion)
                    current_insertion = []

                    # Record the match for P[p_idx]
                    matches[p_idx][mapped_i] = char_t

                    p_idx += 1

            # Commit remaining insertions to the last slot (after P ends)
            if current_insertion:
                slots[p_idx][mapped_i] = "".join(current_insertion)

        # distinct handling for "matches" vs "slots"
        # slots need padding to max length of insertion at that position
        # matches are 1-to-1 (char to char/gap)

        # Construct final rows
        # Row 0 is Pivot
        # Rows 1..N-1 are Others (in order of other_indices)

        final_rows = [[] for _ in range(len(self.texts))]
        pivot_row_idx = pivot_idx
        other_row_indices = other_indices

        for k in range(len(P) + 1):
            # 1. Process Insertions (Slots) at position k
            # Find max length of insertion across all other texts at this slot
            max_ins_len = 0
            for ins_str in slots[k]:
                if len(ins_str) > max_ins_len:
                    max_ins_len = len(ins_str)

            if max_ins_len > 0:
                # Pivot has gaps here (it didn't have these chars)
                final_rows[pivot_row_idx].append(self.gap_char * max_ins_len)

                for mapped_i, original_i in enumerate(other_row_indices):
                    ins_str = slots[k][mapped_i]
                    # align left, pad right with gaps
                    padding = max_ins_len - len(ins_str)
                    final_rows[original_i].append(ins_str + (self.gap_char * padding))

            # 2. Process Match at matched P[k] (if k < len(P))
            if k < len(P):
                # Pivot has P[k]
                final_rows[pivot_row_idx].append(P[k])

                for mapped_i, original_i in enumerate(other_row_indices):
                    match_char = matches[k][mapped_i]
                    # If match_char was empty (shouldn't be if logic is correct), assume gap?
                    # logic ensures matches is filled for 0..len(P)-1
                    final_rows[original_i].append(match_char)

        # Join lists
        final_strings = ["".join(row) for row in final_rows]

        # Pack results
        results = []
        for i, (tid, _) in enumerate(self.texts):
            results.append((tid, final_strings[i]))

        return results
