
import os
import subprocess

# ---------- Util: Pemuat .env tanpa dependency ----------
def load_dotenv(dotenv_path=".env"):
    """
    Memuat variabel dari file .env ke os.environ.
    Format: KEY=VALUE (mendukung spasi setelah '='; baris diawali '#' diabaikan).
    Tidak menimpa os.environ yang sudah ada.
    """
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # Buang kutip jika ada
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                # Jangan override jika sudah ada
                if key not in os.environ:
                    os.environ[key] = val
    except Exception:
        # Silent fail untuk keamanan & robustnes
        pass


class ThumbnailGenerator:
    def __init__(self, font_path=None, ffmpeg_exe=None, assets_folder=None):
        """
        Thumbnail Generator:
        - Membuat Before/After thumbnail dari video.
        - (Opsional) Overlay character PNG setelah green screen #00FF33 dihapus.

        Menggunakan .env dengan variabel:
          - FFMPEG_EXE: path ke ffmpeg executable (Windows/Unix).
          - ASSETS_FOLDER: folder aset proyek.
          - FONT_PATH: path font ttf/otf yang digunakan untuk drawtext.

        Prioritas pemilihan font:
          1) argumen font_path eksplisit (jika diberikan),
          2) env FONT_PATH,
          3) gabungan ASSETS_FOLDER + "./fonts/Montserrat-ExtraBoldItalic.ttf",
          4) fallback "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf".
        """
        # Muat .env terlebih dahulu
        load_dotenv()

        # Resolve ffmpeg executable
        self.ffmpeg_exe = (
            ffmpeg_exe
            or os.environ.get("FFMPEG_EXE")
            or "ffmpeg"  # fallback ke ffmpeg di PATH
        )

        # Resolve assets folder dari env atau argumen
        self.assets_folder = assets_folder or os.environ.get("ASSETS_FOLDER")

        # Resolve font path menurut prioritas
        env_font = os.environ.get("FONT_PATH")
        if font_path:
            self.font_path = font_path
        elif env_font:
            self.font_path = env_font
        elif self.assets_folder:
            # Default yang diminta: ./Assets/fonts/Montserrat-ExtraBoldItalic.ttf
            # Jika ASSETS_FOLDER=E:/Tools/PRoj/Assets -> gabungkan fonts/Montserrat-ExtraBoldItalic.ttf
            self.font_path = os.path.join(self.assets_folder, "fonts", "Montserrat-ExtraBoldItalic.ttf")
        else:
            self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        # Normalisasi path agar aman lintas OS (Windows/Unix)
        self.font_path = os.path.normpath(self.font_path)
        self.ffmpeg_exe = os.path.normpath(self.ffmpeg_exe)

    def generate(
        self,
        video_path,
        output_path,
        character_png_path=None,
        # Param keying untuk green screen #00FF33 (0x00FF33)
        key_color="0x00FF33",
        similarity=0.25,   # toleransi warna (0.0 - 1.0)
        blend=0.08,        # kelembutan tepi (feather/spill)
        # Ukuran karakter saat overlay; rasio aspek dipertahankan (lebar otomatis)
        char_target_height=720
    ):
        """
        Membuat thumbnail Before/After:
          1) Ekstrak frame pertama & terakhir dari video.
          2) Panel kiri = BEFORE (mirror/hflip), panel kanan = AFTER.
          3) Garis pembatas di tengah.
          4) (Opsional) Keying #00FF33 untuk character.png lalu overlay center di kanvas 1920x1080.

        :param video_path: Path video input.
        :param output_path: Path file thumbnail output (jpg/png).
        :param character_png_path: Path PNG dengan green screen #00FF33. Jika None/tidak ada, tidak di-overlay.
        :param key_color: Warna kunci (hex '0xRRGGBB').
        :param similarity: Toleransi keying (semakin besar semakin agresif).
        :param blend: Softness/feathering tepi alpha.
        :param char_target_height: Tinggi target karakter saat overlay (rasio dipertahankan).
        :return: output_path jika sukses, else None.
        """
        if not os.path.exists(video_path):
            print("⚠️ Thumbnail: Video path tidak ditemukan.")
            return None

        # File temporer frame awal/akhir
        start_img = video_path + "_start.jpg"
        end_img = video_path + "_end.jpg"

        try:
            # 1. Ekstrak frame pertama (Before)
            subprocess.run(
                [
                    self.ffmpeg_exe, '-y', '-i', video_path,
                    '-vframes', '1', '-q:v', '2', start_img
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            # 2. Ekstrak frame terakhir (After)
            subprocess.run(
                [
                    self.ffmpeg_exe, '-y', '-sseof', '-1', '-i', video_path,
                    '-update', '1', '-q:v', '2', end_img
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            if not os.path.exists(start_img) or not os.path.exists(end_img):
                print("⚠️ Thumbnail: Gagal ekstrak frame awal/akhir.")
                return None

            # 3. Susun filter_complex
            # Kanvas akhir diharapkan 1920x1080 (dua panel 960x1080).
            left_panel = (
                f"[0:v]scale=-1:1080,"
                f"crop=960:1080:(in_w-960)/2:0,"
                f"hflip,"
                f"drawtext=fontfile='{self.font_path}':text='BEFORE':"
                f"fontcolor=red:fontsize=100:x=(w-text_w)/2:y=100:borderw=5:bordercolor=black[left];"
            )

            right_panel = (
                f"[1:v]scale=-1:1080,"
                f"crop=960:1080:(in_w-960)/2:0,"
                f"drawtext=fontfile='{self.font_path}':text='AFTER':"
                f"fontcolor=green:fontsize=100:x=(w-text_w)/2:y=100:borderw=5:bordercolor=black[right];"
            )

            base_stack = (
                f"[left][right]hstack=inputs=2,"
                f"drawbox=x=958:y=0:w=4:h=1080:color=white@1:t=fill[base]"
            )

            use_character = character_png_path and os.path.exists(character_png_path)

            if use_character:
                cmd = [
                    self.ffmpeg_exe, '-y',
                    '-i', start_img,           # [0:v]
                    '-i', end_img,             # [1:v]
                    '-i', character_png_path,  # [2:v]
                    '-filter_complex',
                    (
                        left_panel +
                        right_panel +
                        base_stack + ";" +
                        # Keying #00FF33, pastikan RGBA, scale tinggi
                        f"[2:v]colorkey={key_color}:{similarity}:{blend},"
                        f"format=rgba,"
                        f"scale=-2:{char_target_height}[char];"
                        # Overlay center ke kanvas 1920x1080
                        f"[base][char]overlay=x=(W-w)/2:y=(H-h)/2:eval=init[out]"
                    ),
                    '-map', '[out]',
                    '-q:v', '2',
                    output_path
                ]
            else:
                cmd = [
                    self.ffmpeg_exe, '-y',
                    '-i', start_img,           # [0:v]
                    '-i', end_img,             # [1:v]
                    '-filter_complex',
                    (
                        left_panel +
                        right_panel +
                        base_stack.replace("[base]", "[out]")
                    ),
                    '-map', '[out]',
                    '-q:v', '2',
                    output_path
                ]

            # 4. Jalankan ffmpeg
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            return output_path if os.path.exists(output_path) else None

        except Exception as e:
            print(f"❌ Thumbnail Error: {e}")
            return None

        finally:
            # Bersihkan file temporer
            for f in (start_img, end_img):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass


# --------- Contoh penggunaan langsung (opsional) ---------
# if __name__ == "__main__":
#     gen = ThumbnailGenerator()
#     out = gen.generate(
#         video_path="input_video.mp4",
#         output_path="thumbnail.jpg",
#         character_png_path="character.png",  # jika ingin overlay
#         key_color="0x00FF33",
#         similarity=0.25,
#         blend=0.08,
#         char_target_height=720
#     )
#     print("Output:", out)
