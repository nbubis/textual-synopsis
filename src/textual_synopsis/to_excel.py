import glob
import pandas as pd
import os
import openpyxl
from openpyxl.styles import Font


def load_aligned_texts(directory="."):
    files = sorted(glob.glob(os.path.join(directory, "aligned_*.txt")))
    texts = []

    for f in files:
        with open(f, "r", encoding="utf-8") as f_obj:
            content = f_obj.read()
            # The filenames are aligned_XYZ.txt. Clean name for row label
            name = os.path.basename(f).replace("aligned_", "").replace(".txt", "")
            texts.append({"name": name, "content": content})

    return texts


def align_to_words(texts):
    if not texts:
        return []

    # Verify lengths
    length = len(texts[0]["content"])
    for t in texts:
        if len(t["content"]) != length:
            raise ValueError(
                f"Length mismatch: {t['name']} has {len(t['content'])} vs {length}"
            )

    # Matrix of words
    rows = [[] for _ in texts]

    # Current word buffer for each row
    current_words = [[] for _ in texts]

    gap_char = "@"  # Hardcoded based on lib/genalog_alignment.py

    for i in range(length):
        chars = [t["content"][i] for t in texts]

        # Check if this column triggers a word break
        # Break if ANY text has a space
        is_break = any(c == " " for c in chars)

        if is_break:
            # Commit current words
            for row_idx in range(len(texts)):
                word = "".join(current_words[row_idx])
                # Filter out gaps? or keep them?
                # User wants "single word". Gaps are not words.
                # If word is "abc@@", it should be "abc".
                # If word is "@@@", it becomes "".
                clean_word = word.replace(gap_char, "")
                rows[row_idx].append(clean_word)
                current_words[row_idx] = []
        else:
            # Append characters
            for row_idx, char in enumerate(chars):
                # We append everything, including gaps, and clean at commit time
                # Or clean now? No, keep logic simple.
                if char != " ":  # Don't append the space itself?
                    # genalog alignment might align ' ' with ' '.
                    # If we break on space, we consume the space.
                    # What if ' ' aligns with '@'?
                    # Then '@' is effectively a space holder.
                    # We should NOT append '@' if it aligns to space.
                    # But here we are in "else" (non-break).
                    # Wait, if is_break is True, we commit.
                    # What happens to the character at `i`?
                    # It is a space (or aligned gap). It should be consumed as delimiter.
                    pass

            # Oh wait.
            # If `chars` has ' ' at row 0, and 'X' at row 1.
            # This is a conflict! space shouldn't align with char usually.
            # But if it does?
            # 'My cat'
            # 'Mypcat'
            # Aligned: 'My cat'
            #          'Mypcat'
            # At space: row 0 is ' ', row 1 is 'p'.
            # If we break: row 0 commits "My", row 1 commits "My".
            # Next word starts: row 0 starts "cat", row 1 starts "cat" (with 'p' lost?)
            # NO. 'p' must belong to one of them.
            # If ' ' aligns with 'p' (substitution), then 'p' is part of the word? Or start of next?
            # Space usually treated as delimiter. 'p' becomes a delimiter? No.
            #
            # In our case, with Star Alignment and gaps:
            # Space should align with Space or Gap.
            # If Space aligns with Char, it's a Substitution. Genalog penalty for Space-Mismatch is high?
            # "SPACE_MISMATCH_PENALTY = 0.1" in addition to mismatch.
            # So likely space aligns with space or gap.
            #
            # Assumption: Space aligns only with Space or Gap.
            # If so, the column `i` is a delimiter column.
            # We discard `chars[i]` (spaces and gaps).
            pass

            if not is_break:
                for row_idx, char in enumerate(chars):
                    current_words[row_idx].append(char)

    # Commit last word
    for row_idx in range(len(texts)):
        word = "".join(current_words[row_idx])
        clean_word = word.replace(gap_char, "")
        rows[row_idx].append(clean_word)

    return rows


def create_printable_chunks(df, chunk_size=20):
    """
    Create a printable version of the DataFrame by chunking columns.

    Args:
        df: DataFrame with sources as rows and words as columns
        chunk_size: Number of word columns per chunk (default 20 for A4 landscape)

    Returns:
        DataFrame with chunks stacked vertically, separated by blank rows
    """
    num_cols = len(df.columns)
    max_cols = chunk_size  # Maximum columns in any chunk
    chunks = []

    # Split into chunks, padding each to the same width
    for start_col in range(0, num_cols, chunk_size):
        end_col = min(start_col + chunk_size, num_cols)
        chunk_df = df.iloc[:, start_col:end_col].copy()

        # Pad chunk with empty columns to reach chunk_size
        cols_to_add = max_cols - len(chunk_df.columns)
        if cols_to_add > 0:
            for j in range(cols_to_add):
                chunk_df[len(chunk_df.columns)] = ""

        # Reset column names to 0, 1, 2, ... for consistent alignment
        chunk_df.columns = range(len(chunk_df.columns))
        chunks.append(chunk_df)

    # Stack chunks vertically with blank rows between them
    result_chunks = []
    for i, chunk in enumerate(chunks):
        result_chunks.append(chunk)
        if i < len(chunks) - 1:  # Add blank row between chunks (except after last)
            # Create a blank row with empty strings
            blank_row = pd.DataFrame(
                [[""] * max_cols], columns=range(max_cols), index=[""]
            )
            result_chunks.append(blank_row)

    return pd.concat(result_chunks, axis=0)


def create_excel_from_aligned(aligned_dir, output_file):
    texts = load_aligned_texts(aligned_dir)
    if not texts:
        print(f"No aligned files found in {aligned_dir}")
        return

    print(f"Generating Excel from {len(texts)} files...")
    rows = align_to_words(texts)

    data = {}
    for i, t in enumerate(texts):
        data[t["name"]] = rows[i]

    df = pd.DataFrame.from_dict(data, orient="index")

    # Create Excel with two sheets: Original and Printable
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        # Original sheet - full width
        df.to_excel(writer, sheet_name="Original", header=False)

        # Printable sheet - chunked for A4 landscape
        chunked_df = create_printable_chunks(df, chunk_size=20)
        chunked_df.to_excel(writer, sheet_name="Printable", header=False)

    # Post-process with openpyxl for formatting
    wb = openpyxl.load_workbook(output_file)

    # Apply formatting to both sheets
    for sheet_name in ["Original", "Printable"]:
        ws = wb[sheet_name]

        # Set Right-to-Left direction
        ws.sheet_view.rightToLeft = True

        # Bold the first column (Column A - source names)
        bold_font = Font(bold=True)
        for cell in ws["A"]:
            cell.font = bold_font

    wb.save(output_file)
    print(f"Written Excel alignment to {output_file}")
    print(f"  - 'Original' tab: Full alignment ({len(df.columns)} columns)")
    print(f"  - 'Printable' tab: Chunked for A4 printing (20 columns per chunk)")


def main():
    create_excel_from_aligned(".", "alignment_table.xlsx")


if __name__ == "__main__":
    main()
