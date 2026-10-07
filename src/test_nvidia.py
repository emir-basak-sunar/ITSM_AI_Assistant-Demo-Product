"""NVIDIA Nemotron duman testi. Anahtarı .env icine NVIDIA_API_KEY=nvapi-... yazin.

    .\\.venv\\Scripts\\python.exe src\\test_nvidia.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(SRC / ".env")

from llm_engine import NVIDIA_MODEL, call_nvidia, is_llm_active


def main() -> None:
    if not is_llm_active():
        print("NVIDIA_API_KEY bos. Proje kokundeki .env dosyasina sunu yazin:")
        print("  NVIDIA_API_KEY=nvapi-...")
        print("  NVIDIA_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        print("  ASSISTANT_USE_LLM=1")
        sys.exit(1)

    print(f"Model: {NVIDIA_MODEL}")
    text = call_nvidia(
        "VPN'e baglanirken sertifika hatasi aliyorum, kisa 3 adim oner.",
        system_prompt="Sen kurumsal bir ITSM L1 Destek Uzmanisin. Turkce, kisa ve net yaz.",
        timeout=60.0,
        max_tokens=400,
    )
    if not text:
        print("Cevap gelmedi. Anahtari, model adini ve NVIDIA konsol hatasini kontrol edin.")
        sys.exit(1)
    print("---")
    print(text)


if __name__ == "__main__":
    main()
