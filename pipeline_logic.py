import argparse
import os
import sys
from multi_align import load_texts_from_directory, StarAligner
from to_excel import create_excel_from_aligned


def run_alignment_pipeline(input_dir, output_dir):
    print(f"Loading texts from {input_dir}...")
    texts = load_texts_from_directory(input_dir)

    if len(texts) < 2:
        print("Error: Need at least 2 text files to align.")
        return False

    print(f"Found {len(texts)} files. Starting alignment...")

    aligner = StarAligner(texts)
    results = aligner.align()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Saving aligned files to {output_dir}...")
    for filename, content in results:
        base, ext = os.path.splitext(filename)
        out_filename = f"aligned_{base}{ext}"
        out_path = os.path.join(output_dir, out_filename)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

    print("Alignment complete.")

    # Generate Excel
    excel_path = os.path.join(output_dir, "alignment_table.xlsx")
    create_excel_from_aligned(output_dir, excel_path)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Align multiple text files from a directory."
    )
    parser.add_argument("input_dir", help="Directory containing text files to align.")
    parser.add_argument(
        "--output-dir",
        help="Directory to save aligned files. Defaults to input_dir/aligned.",
        default=None,
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)

    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.join(input_dir, "aligned")

    success = run_alignment_pipeline(input_dir, output_dir)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
