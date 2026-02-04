import streamlit as st
import tempfile
import os
import shutil
from lib.pipeline import run_alignment_pipeline

st.title("Align Text Files")

st.markdown("""
Upload multiple text files to align them.
- Format: Plain text files (`.txt`)
- Requirement: At least 2 files
- Output: An Excel sheet (`alignment_table.xlsx`) with aligned words.
""")

uploaded_files = st.file_uploader(
    "Choose text files", accept_multiple_files=True, type=["txt"]
)

if uploaded_files:
    if len(uploaded_files) < 2:
        st.warning("Please upload at least 2 files to align.")
    else:
        if st.button("Align Files"):
            with st.spinner("Processing..."):
                # Create a temporary directory for the entire process
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_dir = os.path.join(tmpdir, "input")
                    output_dir = os.path.join(tmpdir, "output")
                    os.makedirs(input_dir)
                    # output_dir will be created by pipeline

                    # Save uploaded files
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(input_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    st.info(f"Aligning {len(uploaded_files)} files...")

                    # Run alignment
                    success = run_alignment_pipeline(input_dir, output_dir)

                    if success:
                        excel_path = os.path.join(output_dir, "alignment_table.xlsx")
                        if os.path.exists(excel_path):
                            st.success("Alignment complete!")

                            with open(excel_path, "rb") as f:
                                st.download_button(
                                    label="Download Alignment Excel",
                                    data=f,
                                    file_name="alignment_table.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                )
                        else:
                            st.error("Alignment finished but Excel file was not found.")
                    else:
                        st.error("Alignment failed. Please check your files.")
