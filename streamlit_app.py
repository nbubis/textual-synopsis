import streamlit as st
import tempfile
import os
from textual_synopsis.pipeline import run_alignment_pipeline
from textual_synopsis.to_excel import add_printable_tab_to_excel

st.title("Textual Synopsis Tools")

st.markdown("""
<style>
    /* Hide the default Streamlit file uploader file list and pagination */
    [data-testid="stFileUploaderDropzone"] + div {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Align Text Files", "Add Printable Tab"])

with tab1:
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
        import pandas as pd
        
        # Custom display for all uploaded files showing many at once instead of just 3
        with st.expander(f"View {len(uploaded_files)} Uploaded Files", expanded=True):
            file_data = [{"File Name": f.name, "Size (KB)": round(f.size / 1024, 1)} for f in uploaded_files]
            # Height allows for ~20 files before scrolling
            st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True, height=min(800, max(150, len(uploaded_files)*36 + 43)))

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

with tab2:
    st.markdown("""
    Upload an existing Excel (.xlsx) file to add a `Printable` tab to it.
    The new tab will contain the data from the **first** sheet in the document, properly chunked for wide printing.
    """)
    
    uploaded_excel = st.file_uploader(
        "Choose an Excel file", accept_multiple_files=False, type=["xlsx"]
    )
    
    if uploaded_excel:
        if st.button("Generate Printable Tab"):
            with st.spinner("Processing Excel File..."):
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.xlsx")
                    output_path = os.path.join(tmpdir, "output.xlsx")
                    
                    with open(input_path, "wb") as f:
                        f.write(uploaded_excel.getbuffer())
                    
                    try:
                        add_printable_tab_to_excel(input_path, output_path)
                        st.success("Printable tab added successfully!")
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download Updated Excel",
                                data=f,
                                file_name=f"printable_{uploaded_excel.name}",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                    except Exception as e:
                        st.error(f"Failed to generate printable tab. Error: {str(e)}")
