import streamlit as st
import os
import tempfile
import subprocess
import json
from openai import OpenAI
import imageio_ffmpeg

st.set_page_config(
    page_title="BY ROMA AI AUTO CLIPPER",
    page_icon="🎬",
    layout="wide"
)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

st.markdown("""
# 🎬 BY ROMA
## AI AUTO CLIPPER
### Smart Video Clipper for Perfume Reviewers
""")

st.write(
    "Ubah video panjang menjadi clip pendek "
    "yang menarik secara otomatis menggunakan AI."
)

api_key = st.text_input(
    "OpenAI API Key",
    type="password",
    help="Masukkan API key OpenAI milikmu."
)

video = st.file_uploader(
    "Upload video reviewer parfum",
    type=["mp4", "mov", "mkv", "avi"]
)

clip_duration = st.selectbox(
    "Durasi setiap clip",
    [15, 30, 45, 60, 90, 120],
    index=1
)

clip_count = st.slider(
    "Jumlah clip yang ingin dibuat",
    1, 20, 5
)

style = st.selectbox(
    "Gaya pemilihan clip",
    [
        "Viral Hook",
        "Review Jujur",
        "Storytelling",
        "Promosi Produk",
        "Reaksi dan Ekspresi",
        "Campuran Semua"
    ]
)

if st.button("🚀 MULAI AUTO CLIPPING", type="primary"):

    if not api_key:
        st.error("Masukkan OpenAI API Key terlebih dahulu.")

    elif not video:
        st.error("Upload video terlebih dahulu.")

    else:
        client = OpenAI(api_key=api_key)

        with tempfile.TemporaryDirectory() as temp:

            input_path = os.path.join(temp, "video.mp4")

            with open(input_path, "wb") as f:
                f.write(video.getbuffer())

            st.info("Memeriksa durasi video...")

            probe = subprocess.run(
                [
                    FFMPEG, "-i", input_path,
                    "-f", "null", "-"
                ],
                capture_output=True,
                text=True
            )

            import re
            match = re.search(
                r"Duration: (\d+):(\d+):(\d+)",
                probe.stderr
            )

            if not match:
                st.error("Tidak dapat membaca durasi video.")
                st.stop()

            hours, minutes, seconds = map(int, match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds

            if total_seconds > 3600:
                st.error("Durasi maksimal video adalah 60 menit.")
                st.stop()

            st.success("Video berhasil dibaca.")

            transcript_parts = []
            progress = st.progress(0)

            chunk_seconds = 480
            total_chunks = (total_seconds + chunk_seconds - 1) // chunk_seconds

            for i in range(total_chunks):

                start = i * chunk_seconds
                audio_path = os.path.join(temp, f"audio_{i}.mp3")

                subprocess.run(
                    [
                        FFMPEG, "-y",
                        "-ss", str(start),
                        "-i", input_path,
                        "-t", str(chunk_seconds),
                        "-vn",
                        "-ac", "1",
                        "-b:a", "48k",
                        audio_path
                    ],
                    capture_output=True,
                    check=True
                )

                with open(audio_path, "rb") as audio:
                    result = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        response_format="text"
                    )

                transcript_parts.append(
                    f"[Mulai detik {start}]\n{result}"
                )

                progress.progress((i + 1) / total_chunks)

            transcript = "\n".join(transcript_parts)

            st.success("Transkripsi selesai.")

            prompt = f"""
            Kamu adalah editor video profesional khusus reviewer parfum.

            Analisis transkrip berikut:
            {transcript}

            Gaya clip: {style}
            Jumlah clip: {clip_count}
            Durasi target setiap clip: {clip_duration} detik.

            Pilih momen paling menarik berdasarkan:
            - Hook yang kuat.
            - Reaksi dan ekspresi.
            - Informasi aroma parfum.
            - Pendapat yang menarik.
            - Storytelling.
            - Potensi engagement.

            Buat JSON dengan format:
            {{
              "clips": [
                {{
                  "start": 10,
                  "end": 40,
                  "title": "Judul clip",
                  "reason": "Alasan dipilih"
                }}
              ]
            }}

            Waktu start dan end harus dalam detik video asli.
            Jangan memilih bagian di luar durasi video.
            Pilih momen yang tidak berulang.
            """

            with st.spinner("AI sedang mencari momen terbaik..."):

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                data = json.loads(
                    response.choices[0].message.content
                )

            clips = data.get("clips", [])[:clip_count]

            if not clips:
                st.warning("AI belum menemukan clip yang sesuai.")
                st.stop()

            st.subheader("🎞️ HASIL AI CLIPPING")

            for index, clip in enumerate(clips, 1):

                start = max(0, float(clip["start"]))
                end = min(total_seconds, float(clip["end"]))

                if end <= start:
                    continue

                if end - start > clip_duration:
                    end = start + clip_duration

                output_path = os.path.join(
                    temp, f"BYROMA_CLIP_{index}.mp4"
                )

                subprocess.run(
                    [
                        FFMPEG, "-y",
                        "-ss", str(start),
                        "-i", input_path,
                        "-t", str(end - start),
                        "-map", "0:v:0",
                        "-map", "0:a?",
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-c:a", "aac",
                        "-movflags", "+faststart",
                        output_path
                    ],
                    capture_output=True,
                    check=True
                )

                st.markdown(f"### Clip {index}: {clip['title']}")
                st.write(clip["reason"])

                with open(output_path, "rb") as f:
                    clip_bytes = f.read()

                st.video(clip_bytes)

                st.download_button(
                    "⬇️ Download Clip",
                    data=clip_bytes,
                    file_name=f"BYROMA_CLIP_{index}.mp4",
                    mime="video/mp4",
                    key=f"download_{index}"
                )

            st.success("Proses clipping selesai!")
