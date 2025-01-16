
import os
import pandas as pd
import streamlit as st
import SimpleITK as sitk
import webbrowser
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Configure page for better clinical experience
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

def dir_selector(folder_path='.'):
    """Directory selector with session state persistence"""
    dirnames = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
    if 'selected_folder' not in st.session_state:
        st.session_state.selected_folder = None

    selected = st.sidebar.selectbox(
        'Select DICOM Folder',
        dirnames,
        key='folder_selector',
        index=dirnames.index(st.session_state.selected_folder) if st.session_state.selected_folder in dirnames else 0
    )
    
    if selected != st.session_state.selected_folder:
        st.session_state.selected_folder = selected
        st.session_state.is_deidentified = False
        st.session_state.deidentified_data = None
        st.session_state.deidentified_metadata = None
        st.rerun()
    
    return os.path.join(folder_path, selected) if selected else None

def calculate_aspect_ratio(metadata):
    """Calculate proper aspect ratio from DICOM metadata"""
    try:
        pixel_spacing = metadata.get("0028|0030", "")
        if pixel_spacing:
            spacing = [float(x) for x in pixel_spacing.split("\\")]
            return spacing[1] / spacing[0]
        
        rows = float(metadata.get("0028|0010", "512"))
        cols = float(metadata.get("0028|0011", "512"))
        if rows > 0 and cols > 0:
            return rows / cols
            
    except Exception as e:
        print(f"Aspect ratio calculation error: {str(e)}")
    return 1.0

def apply_window_level(image, window_center, window_width):
    """Apply window/level adjustment to image with proper error handling"""
    try:
        window_width = max(1, min(abs(window_width), 4000))
        window_center = max(-1024, min(window_center, 3000))
        
        min_value = float(window_center - window_width / 2)
        max_value = float(window_center + window_width / 2)
        
        image_float = image.astype(float)
        image_windowed = np.clip(image_float, min_value, max_value)
        image_normalized = ((image_windowed - min_value) / (max_value - min_value) * 255)
        
        return image_normalized.astype(np.uint8)
    except Exception as e:
        print(f"Window/level error: {str(e)}")
        return image

def get_default_window_level(metadata):
    """Get default window/level settings from DICOM metadata"""
    try:
        window_center = float(metadata.get("0028|1050", "40"))
        window_width = float(metadata.get("0028|1051", "400"))
        
        if not (-1024 <= window_center <= 3000) or not (1 <= window_width <= 4000):
            return 40, 400
            
        return window_center, window_width
    except:
        return 40, 400

def format_datetime(metadata):
    """Format date and time from DICOM metadata"""
    try:
        date = metadata.get("0008|0023", "") or metadata.get("0008|0020", "")
        time = metadata.get("0008|0033", "") or metadata.get("0008|0030", "")
        
        if date and time:
            date_obj = datetime.strptime(date, "%Y%m%d")
            formatted_date = date_obj.strftime("%b %d, %Y")
            hours, minutes, seconds = time[0:2], time[2:4], time[4:6]
            return f"{formatted_date} | {hours}:{minutes}:{seconds}"
    except:
        return ""
    return ""

def deidentify_dicom_series(reader):
    """De-identify entire DICOM series"""
    tags_to_remove = [
        "0010|0010", "0010|0020", "0010|0030", "0008|0080",
        "0008|0090", "0008|1030", "0008|0050", "0008|0020",
        "0008|0030", "0008|0021", "0008|0031", "0008|1040",
        "0010|0040", "0010|1010", "0008|103E", "0010|2160",
        "0012|0062", "0040|A124",
    ]
    
    deidentified_series = sitk.ImageSeriesReader()
    deidentified_series.SetFileNames(reader.GetFileNames())
    deidentified_series.LoadPrivateTagsOn()
    deidentified_series.MetaDataDictionaryArrayUpdateOn()
    image_series = deidentified_series.Execute()
    
    safe_metadata = []
    for slice_idx in range(len(reader.GetFileNames())):
        slice_metadata = {}
        for key in reader.GetMetaDataKeys(slice_idx):
            if key in tags_to_remove:
                slice_metadata[key] = "REMOVED"
            else:
                slice_metadata[key] = reader.GetMetaData(slice_idx, key)
        safe_metadata.append(slice_metadata)
    
    return image_series, safe_metadata

def plot_slice(vol, slice_ix, metadata, window_center, window_width, use_original=False):
    """Create an interactive plot of a DICOM slice with proper aspect ratio"""
    selected_slice = vol[slice_ix, :, :]
    
    # Only apply window/level if not using original values
    if not use_original:
        selected_slice = apply_window_level(selected_slice, window_center, window_width)
    
    # Get patient name based on de-identification status
    if st.session_state.is_deidentified:
        patient_name = "REMOVED"
    else:
        patient_name = metadata.get("0010|0010", "Anonymous")
    
    datetime_str = format_datetime(metadata)
    total_slices = vol.shape[0]
    aspect_ratio = calculate_aspect_ratio(metadata)
    
    study_desc = metadata.get("0008|1030", "").strip()
    if st.session_state.is_deidentified:
        study_desc = "REMOVED"
    
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
    
    font_size = 12 if st.session_state.get('is_mobile', False) else 14
    
    # Update display text based on whether using original values
    window_level_text = "Original Values" if use_original else f"W: {window_width} L: {window_center}"
    
    annotations = [
        dict(
            x=0, y=1.17,
            xref="paper", yref="paper",
            text=f"Patient: {patient_name}",
            showarrow=False,
            font=dict(size=font_size, color="white"),
            bgcolor="black",
            borderpad=4
        ),
        dict(
            x=0, y=1.08,
            xref="paper", yref="paper",
            text=f"Date: {datetime_str}",
            showarrow=False,
            font=dict(size=font_size, color="white"),
            bgcolor="black",
            borderpad=4
        ),
       
        dict(
            x=1, y=-0.03,
            xref="paper", yref="paper",
            text=f"Slice: {slice_ix + 1}/{total_slices} | {window_level_text}",
            showarrow=False,
            font=dict(size=font_size, color="white"),
            bgcolor="black",
            borderpad=4,
            xanchor='right'
        )
    ]
    
    fig.update_layout(
        annotations=annotations,
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
            scaleratio=aspect_ratio,
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



def main():
    """Main application function"""
    # Initialize session state
    for key in ['is_deidentified', 'deidentified_data', 'deidentified_metadata', 'show_deident_message']:
        if key not in st.session_state:
            st.session_state[key] = None
    
    st.session_state.is_mobile = st.query_params.get('mobile', False)
    
    # Sidebar setup
    st.sidebar.title('CT Contrast Viewer')
    dirname = dir_selector()
    
    if dirname is not None:
        try:
            # Read DICOM series
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(dirname)
            reader.SetFileNames(dicom_names)
            reader.LoadPrivateTagsOn()
            reader.MetaDataDictionaryArrayUpdateOn()
            original_data = reader.Execute()
            original_img = sitk.GetArrayViewFromImage(original_data)
            
            # Handle deidentification
            if st.session_state.is_deidentified and st.session_state.deidentified_data is not None:
                deident_img = sitk.GetArrayViewFromImage(st.session_state.deidentified_data)
                metadata_to_display = st.session_state.deidentified_metadata[0]
            else:
                deident_img = None
                metadata_to_display = {k: reader.GetMetaData(0, k) for k in reader.GetMetaDataKeys(0)}
            
            # Layout controls
            st.sidebar.subheader("Navigation")
            n_slices = original_img.shape[0]
            slice_ix = st.sidebar.slider('Slice', 1, n_slices, int(n_slices/2)) - 1
            
            # Clinical controls
            st.sidebar.subheader("Contrast Settings")
            
            # CT contrast-specific presets
            preset_options = {
                "Standard": (40, 400),
                "Soft Tissue": (50, 450),
                "Contrast Enhanced": (100, 700),
                "Perfusion": (150, 800),
                "Custom": "custom"
            }
            
            selected_preset = st.sidebar.selectbox(
                "Window Preset",
                options=list(preset_options.keys()),
                index=0
            )
         
            # Window/level handling
            if selected_preset == "Custom":
                # Get original window/level values from DICOM metadata
                default_center, default_width = get_default_window_level(metadata_to_display)
                
                window_center = st.sidebar.slider(
                    "Window Center",
                    min_value=-1024,
                    max_value=3000,
                    value=int(default_center)  # Use DICOM default
                )
                window_width = st.sidebar.slider(
                    "Window Width",
                    min_value=1,
                    max_value=4000,
                    value=int(default_width)   # Use DICOM default
                )
                
                # Check if sliders have been moved from their default positions
                use_original = (window_center == default_center and 
                              window_width == default_width)
                              
                img_to_display = original_img
            else:
                use_original = False
                window_center, window_width = preset_options[selected_preset]
                img_to_display = deident_img if st.session_state.is_deidentified else original_img
            
            output = st.sidebar.radio('Display', ['Image', 'Metadata'], index=0)
            
            # De-identification control
            if not st.session_state.is_deidentified:
                if st.sidebar.button('De-identify DICOM', use_container_width=True):
                    st.session_state.deidentified_data, st.session_state.deidentified_metadata = deidentify_dicom_series(reader)
                    st.session_state.is_deidentified = True
                    st.session_state.show_deident_message = True
                    st.rerun()
            
            # Display output
            if output == 'Image':
                # Update metadata for current slice
                if st.session_state.is_deidentified and not use_original:
                    metadata_to_display = st.session_state.deidentified_metadata[slice_ix]
                else:
                    metadata_to_display = {k: reader.GetMetaData(slice_ix, k) for k in reader.GetMetaDataKeys(slice_ix)}
                
                fig = plot_slice(
                    img_to_display,
                    slice_ix,
                    metadata_to_display,
                    window_center,
                    window_width,
                    use_original
                )
                
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
                
                # Show de-identification message only once after de-identification
                if st.session_state.show_deident_message:
                    st.success('Series is de-identified. Sensitive metadata has been removed.')
                    st.session_state.show_deident_message = False
            else:
                if st.session_state.is_deidentified and not use_original:
                    metadata_to_display = st.session_state.deidentified_metadata[slice_ix]
                df = pd.DataFrame.from_dict(metadata_to_display, orient='index', columns=['Value'])
                st.dataframe(df, use_container_width=True)
                
                # Show de-identification message only once in metadata view as well
                if st.session_state.show_deident_message:
                    st.success('Series is de-identified. Sensitive metadata has been removed.')
                    st.session_state.show_deident_message = False
                    
        except RuntimeError as e:
            st.error(f'Error loading DICOM data: {str(e)}')

if __name__ == "__main__":
    main()