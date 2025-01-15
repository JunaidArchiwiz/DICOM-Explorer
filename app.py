
import os
import pandas as pd
import streamlit as st
import SimpleITK as sitk
import webbrowser
import plotly.graph_objects as go
from datetime import datetime

# Configure page for better mobile experience
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

def dir_selector(folder_path='.'):
    """Directory selector with session state persistence"""
    dirnames = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
    
    # Initialize selected_folder in session state if it doesn't exist
    if 'selected_folder' not in st.session_state:
        st.session_state.selected_folder = None
    
    # Only update the selected folder if user explicitly changes it
    selected = st.sidebar.selectbox(
        'Select a folder',
        dirnames,
        key='folder_selector',
        index=dirnames.index(st.session_state.selected_folder) if st.session_state.selected_folder in dirnames else 0
    )
    
    # Update session state only if selection changes
    if selected != st.session_state.selected_folder:
        st.session_state.selected_folder = selected
        # Reset de-identification state when folder changes
        st.session_state.is_deidentified = False
        st.session_state.deidentified_data = None
        st.session_state.deidentified_metadata = None
        st.rerun()
    
    return os.path.join(folder_path, selected) if selected else None

def format_datetime(metadata):
    """Format date and time from DICOM metadata"""
    try:
        date = metadata.get("0008|0023", "") or metadata.get("0008|0020", "")
        time = metadata.get("0008|0033", "") or metadata.get("0008|0030", "")
        
        if date and time:
            date_obj = datetime.strptime(date, "%Y%m%d")
            formatted_date = date_obj.strftime("%b %d, %Y")
            
            hours = time[0:2]
            minutes = time[2:4]
            seconds = time[4:6]
            
            return f"{formatted_date} | {hours}:{minutes}:{seconds}"
    except:
        return ""

def plot_slice(vol, slice_ix, metadata):
    """Create an interactive plot of a DICOM slice with responsive design"""
    selected_slice = vol[slice_ix, :, :]
    patient_name = metadata.get("0010|0010", "")
    datetime_str = format_datetime(metadata)
    total_slices = vol.shape[0]
    
    # Make figure responsive
    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            z=selected_slice,
            colorscale='Gray',
            showscale=False,
            hoverongaps=False,
            hoverinfo='z'
        )
    )
    
    # Adjust annotation positions and sizes for mobile
    font_size = 12 if st.session_state.get('is_mobile', False) else 14
    
    fig.update_layout(
        annotations=[
            dict(
                x=0,
                y=1.15,
                xref="paper",
                yref="paper",
                text=patient_name,
                showarrow=False,
                font=dict(size=font_size, color="white"),
                bgcolor="black",
                borderpad=4
            ),
            dict(
                x=0,
                y=1.1,
                xref="paper",
                yref="paper",
                text=datetime_str,
                showarrow=False,
                font=dict(size=font_size, color="white"),
                bgcolor="black",
                borderpad=4
            ),
            dict(
                x=0,
                y=-0.03,
                xref="paper",
                yref="paper",
                text=f"Slice {slice_ix + 1}/{total_slices}",
                showarrow=False,
                font=dict(size=font_size, color="white"),
                bgcolor="black",
                borderpad=4
            )
        ],
        autosize=True,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='black',
        plot_bgcolor='black',
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            fixedrange=False,
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            scaleanchor='x',
            fixedrange=False,
        ),
        dragmode='pan',
        newshape=dict(
            line_color='red',
            fillcolor='rgba(255, 0, 0, 0.2)',
            opacity=0.8,
        ),
    )
    
    return fig

def deidentify_dicom_series(reader):
    """
    De-identify entire DICOM series
    """
    tags_to_remove = [
        "0010|0010", "0010|0020", "0010|0030", "0008|0080",
        "0008|0090", "0008|1030", "0008|0050", "0008|0020",
        "0008|0030", "0008|0021", "0008|0031", "0008|1040",
        "0010|0040", "0010|1010", "0008|103E", "0010|2160",
        "0012|0062", "0040|A124",
    ]
    
    # Create a new series with deidentified metadata
    deidentified_series = sitk.ImageSeriesReader()
    deidentified_series.SetFileNames(reader.GetFileNames())
    deidentified_series.LoadPrivateTagsOn()
    deidentified_series.MetaDataDictionaryArrayUpdateOn()
    
    # Read the entire series
    image_series = deidentified_series.Execute()
    
    # Create safe metadata for all slices
    safe_metadata = []
    for slice_idx in range(len(reader.GetFileNames())):
        slice_metadata = {}
        for key in reader.GetMetaDataKeys(slice_idx):
            slice_metadata[key] = "REMOVED" if key in tags_to_remove else reader.GetMetaData(slice_idx, key)
        safe_metadata.append(slice_metadata)
    
    return image_series, safe_metadata

# Main Streamlit App
def main():
    # Initialize session state variables if they don't exist
    for key in ['is_deidentified', 'deidentified_data', 'deidentified_metadata']:
        if key not in st.session_state:
            st.session_state[key] = None
    
    # Detect if running on mobile
    st.session_state.is_mobile = st.query_params.get('mobile', False)
    
    st.sidebar.title('DICOM Viewer')
    dirname = dir_selector()
    
    if st.sidebar.button("Open 3D Visualization", use_container_width=True):
        webbrowser.open("http://127.0.0.1:8050/")
        st.success("Dash app opened in your browser!")

    if dirname is not None:
        try:
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(dirname)
            reader.SetFileNames(dicom_names)
            reader.LoadPrivateTagsOn()
            reader.MetaDataDictionaryArrayUpdateOn()
            data = reader.Execute()
            
            # Use deidentified data if it exists in session state
            if st.session_state.is_deidentified and st.session_state.deidentified_data is not None:
                img = sitk.GetArrayViewFromImage(st.session_state.deidentified_data)
            else:
                img = sitk.GetArrayViewFromImage(data)
            
            # Create two columns for controls on mobile
            col1, col2 = st.sidebar.columns(2)
            
            with col1:
                n_slices = img.shape[0]
                slice_ix = st.slider('Slice', 1, n_slices, int(n_slices/2)) - 1
            
            with col2:
                # Only show deidentify button if not already deidentified
                if not st.session_state.is_deidentified:
                    if st.button('De-identify DICOM', use_container_width=True):
                        st.session_state.deidentified_data, st.session_state.deidentified_metadata = deidentify_dicom_series(reader)
                        st.session_state.is_deidentified = True
                        st.rerun()
                
                output = st.radio('Output', ['Image', 'Metadata'], index=0)
            
            # Use appropriate metadata based on deidentification state
            if st.session_state.is_deidentified:
                metadata_to_display = st.session_state.deidentified_metadata[slice_ix]
            else:
                metadata_to_display = {k: reader.GetMetaData(slice_ix, k) for k in reader.GetMetaDataKeys(slice_ix)}
            
            if output == 'Image':
                fig = plot_slice(img, slice_ix, metadata_to_display)
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        'scrollZoom': True,
                        'displayModeBar': True,
                        'modeBarButtonsToAdd': [
                            'drawline',
                            'drawopenpath',
                            'drawclosedpath',
                            'drawcircle',
                            'drawrect',
                            'eraseshape'
                        ]
                    }
                )
                
                if st.session_state.is_deidentified:
                    st.success('Series is de-identified. Sensitive metadata has been removed.')
            else:
                df = pd.DataFrame.from_dict(metadata_to_display, orient='index', columns=['Value'])
                st.dataframe(df, use_container_width=True)
                if st.session_state.is_deidentified:
                    st.success('Series is de-identified. Sensitive metadata has been removed.')
                    
        except RuntimeError:
            st.error('This does not look like a DICOM folder!')

if __name__ == "__main__":
    main()
