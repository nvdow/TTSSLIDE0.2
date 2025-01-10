import streamlit as st
from gtts import gTTS
from io import BytesIO
import tempfile
import os
import ffmpeg
from PIL import Image
import subprocess

def single_slide_tts_to_mp4():
    st.header("Single-Slide TTS to MP4")

    uploaded_file = st.file_uploader(
        "Upload your slide image (JPG or PNG):", 
        type=["jpg", "jpeg", "png"]
    )
    text_input = st.text_area("Enter the text for this slide (TTS):")

    if st.button("Generate MP4"):
        if not uploaded_file:
            st.warning("Please upload an image slide.")
            return
        if not text_input.strip():
            st.warning("Please enter some text.")
            return

        # Convert image to RGB if needed and ensure dimensions are even
        with Image.open(uploaded_file) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            width, height = img.size
            new_width = width if width % 2 == 0 else width - 1
            new_height = height if height % 2 == 0 else height - 1
            img = img.resize((new_width, new_height))

            temp_image_path = os.path.join(tempfile.gettempdir(), "uploaded_slide.jpg")
            img.save(temp_image_path)

        # Generate TTS audio (MP3)
        tts = gTTS(text_input, lang="en")
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)

        temp_audio_path = os.path.join(tempfile.gettempdir(), "tts_audio.mp3")
        with open(temp_audio_path, "wb") as f:
            f.write(audio_fp.read())

        # Define temporary output video path
        temp_output_path = os.path.join(tempfile.gettempdir(), "tts_slide.mp4")

        # Use ffmpeg to combine image + audio into MP4
        try:
            input_image = ffmpeg.input(temp_image_path, loop=1, framerate=1)
            input_audio = ffmpeg.input(temp_audio_path)

            # Get audio duration
            audio_probe = ffmpeg.probe(temp_audio_path)
            audio_duration = float(
                next(stream for stream in audio_probe['streams'] 
                     if stream['codec_type'] == 'audio')['duration']
            )

            ffmpeg.output(
                input_image,
                input_audio,
                temp_output_path,
                vcodec='libx264',
                pix_fmt='yuv420p',
                shortest=None,
                acodec='aac',
                audio_bitrate='192k',
                t=audio_duration  # Trim video to match audio duration
            ).run(overwrite_output=True)

        except ffmpeg.Error as e:
            error_message = e.stderr.decode('utf-8', 'replace') if e.stderr else str(e)
            st.error(f"Error running ffmpeg: {error_message}")
            return

        # Display and provide download link for the generated MP4
        with open(temp_output_path, "rb") as f:
            mp4_data = f.read()

        st.video(mp4_data)
        st.download_button(
            label="Download MP4",
            data=mp4_data,
            file_name="tts_slide.mp4",
            mime="video/mp4"
        )

        # Clean up temporary files
        os.remove(temp_image_path)
        os.remove(temp_audio_path)
        os.remove(temp_output_path)


def video_clipper_and_combiner():
    st.header("Video Clipper and Combiner (FFmpeg)")

    st.write(
        "Upload multiple video files (e.g., .mp4, .mov, .avi) "
        "in the order you want them concatenated."
    )

    # 1. File uploader
    uploaded_files = st.file_uploader(
        label="Choose your video files",
        type=["mp4", "mov", "avi"],
        accept_multiple_files=True
    )

    # 2. Concatenate videos on button click
    if st.button("Combine Videos"):
        if not uploaded_files:
            st.warning("Please upload at least one video file.")
            return

        # Create temp directory for saving uploaded files
        os.makedirs("temp_videos", exist_ok=True)

        # Save uploaded files to disk and build a list of their paths
        video_paths = []
        for uploaded_file in uploaded_files:
            temp_file_path = os.path.join("temp_videos", uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.read())
            video_paths.append(temp_file_path)

        # Create a file list for FFmpeg
        filelist_path = "filelist.txt"
        with open(filelist_path, "w") as f:
            for path in video_paths:
                # IMPORTANT: Ensure the path is quoted if it contains spaces
                f.write(f"file '{os.path.abspath(path)}'\n")

        # Define the output path
        output_path = "combined_video.mp4"

        # 3. Use FFmpeg to concatenate
        ffmpeg_cmd = [
            "ffmpeg", 
            "-y", 
            "-f", "concat", 
            "-safe", "0", 
            "-i", filelist_path, 
            "-c", "copy", 
            output_path
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            st.success("Videos have been combined successfully!")

            # 4. Provide a download button for the combined video
            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Combined Video",
                    data=f,
                    file_name="final_combined_video.mp4",
                    mime="video/mp4"
                )
        except subprocess.CalledProcessError as e:
            st.error("Error while combining videos:")
            st.error(str(e))

        # Optional: Clean up temporary files
        # for path in video_paths:
        #     os.remove(path)
        # os.remove(filelist_path)


def main():
    st.title("Combined Streamlit App")

    menu = ["Single-Slide TTS to MP4", "Video Clipper and Combiner (FFmpeg)"]
    choice = st.sidebar.selectbox("Select a feature", menu)

    if choice == "Single-Slide TTS to MP4":
        single_slide_tts_to_mp4()
    elif choice == "Video Clipper and Combiner (FFmpeg)":
        video_clipper_and_combiner()


if __name__ == "__main__":
    main()
