import subprocess
import threading
import os

class MediaEngine:
    def __init__(self):
        self.audio_bitrate_k = 192

    def get_duration(self, input_path):
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", input_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        return float(result.stdout.strip())

    def calculate_video_bitrate(self, target_mb, duration_s):
        total_bitrate = (target_mb * 8192) / duration_s
        video_bitrate = total_bitrate - self.audio_bitrate_k
        return max(50, int(video_bitrate * 0.97))

    def compress_video(self, input_path, output_path, target_mb, progress_callback):
        def worker():
            try:
                duration_s = self.get_duration(input_path)
                duration_us = duration_s * 1000000  # FFmpeg envia o progresso em microsegundos
                v_bitrate = self.calculate_video_bitrate(target_mb, duration_s)
                
                base_cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-c:v", "libx264", 
                    "-b:v", f"{v_bitrate}k",
                    "-preset", "slow",
                    "-profile:v", "high",
                    "-progress", "pipe:1", # Joga o progresso para o stdout
                    "-nostats"
                ]
                
                def run_pass(cmd, pass_num):
                    # Popen permite ler a saída linha por linha enquanto o processo roda
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
                    
                    for line in process.stdout:
                        if "out_time_us=" in line:
                            try:
                                time_us = int(line.split("=")[1].strip())
                                if time_us > 0:
                                    fraction = min(1.0, time_us / duration_us)
                                    # O passo 1 vai de 0 a 0.5 (50%), o passo 2 de 0.5 a 1.0 (100%)
                                    overall_progress = (fraction / 2.0) + (0.5 if pass_num == 2 else 0.0)
                                    progress_callback(overall_progress)
                            except ValueError:
                                pass
                                
                    process.wait()
                    if process.returncode != 0:
                        raise Exception(f"Falha no Passo {pass_num}")

                # PASSO 1
                cmd_pass1 = base_cmd + ["-pass", "1", "-an", "-f", "null", os.devnull]
                run_pass(cmd_pass1, 1)
                
                # PASSO 2
                cmd_pass2 = base_cmd + ["-pass", "2", "-c:a", "aac", "-b:a", f"{self.audio_bitrate_k}k", output_path]
                run_pass(cmd_pass2, 2)
                
                # Limpeza
                for log_file in ["ffmpeg2pass-0.log", "ffmpeg2pass-0.log.mbtree"]:
                    if os.path.exists(log_file):
                        os.remove(log_file)
                        
                progress_callback(1.0)
            except Exception as e:
                print(f"Erro na compressão: {e}")
                progress_callback(-1.0)

        threading.Thread(target=worker, daemon=True).start()