from Bio import Align


def test_align():
    aligner = Align.PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 1.0
    aligner.mismatch_score = -0.5
    aligner.open_gap_score = -0.5
    aligner.extend_gap_score = -0.5

    seq1 = "Boston"
    seq2 = "B oston"

    alignments = aligner.align(seq1, seq2)

    print(f"Found {len(alignments)} alignments")

    if len(alignments) > 0:
        aln = alignments[0]
        # Attempt to get aligned strings
        # alignment objects in newer biopython are array-like
        # aln[0] should be the aligned seq1
        # aln[1] should be the aligned seq2

        print("Using slicing:")
        try:
            aligned_seq1 = aln[0]
            aligned_seq2 = aln[1]
            print(f"Seq1: '{aligned_seq1}'")
            print(f"Seq2: '{aligned_seq2}'")

            # Check gap char
            print(f"Gap char used: {'-' if '-' in aligned_seq1 else '?'}")

        except Exception as e:
            print(f"Slicing failed: {e}")

        # Inspecting coordinates
        print(f"Coordinates: {aln.coordinates}")


if __name__ == "__main__":
    test_align()
