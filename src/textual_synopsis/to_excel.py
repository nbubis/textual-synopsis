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

    rows = []
    gap_char = "@"

    for t in texts:
        content = t["content"].strip()
        if not content:
            words = []
        else:
            words = content.split(" ")
        
        clean_words = ["" if w == gap_char else w for w in words]
        rows.append(clean_words)

    if not rows:
        return []

    length = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != length:
            raise ValueError(
                f"Length mismatch: {texts[i]['name']} has {len(r)} words vs {length} words"
            )

    # Filter out columns where all rows are empty strings
    valid_cols = []
    for col_idx in range(length):
        if any(rows[row_idx][col_idx] != "" for row_idx in range(len(rows))):
            valid_cols.append(col_idx)

    filtered_rows = [[] for _ in rows]
    for col_idx in valid_cols:
        for row_idx in range(len(rows)):
            filtered_rows[row_idx].append(rows[row_idx][col_idx])

    return filtered_rows


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
