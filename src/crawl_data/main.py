import sys
from pathlib import Path

# Allow sibling-module imports when run directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config, PROJECT_ROOT   # noqa: E402
from pipeline import TTSDatasetPipeline   # noqa: E402


def main():
    """Entry point: load config, read URLs, and run the pipeline."""
    config = Config()

    print("\n" + "═" * 50)
    print("Vietnamese TTS Dataset Pipeline")
    print("═" * 50)
    print(f"Model:      {config.whisper_model}")
    print(f"Device:     {config.device}")
    print(f"Compute:    {config.compute_type}")
    print(f"Language:   {config.language}")
    print(f"Seg window: [{config.min_segment_duration}s, {config.max_segment_duration}s]")
    print("═" * 50)

    urls_file = PROJECT_ROOT / "src" / "crawl_data" / "youtube_urls.txt"
    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            youtube_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        print(f"{urls_file} not found. Create it with one YouTube URL per line.")
        sys.exit(1)

    if not youtube_urls:
        print("No URLs found in youtube_urls.txt")
        sys.exit(1)

    print(f"{len(youtube_urls)} URL(s) queued\n")

    pipeline = TTSDatasetPipeline(config)
    pipeline.run(youtube_urls)


if __name__ == "__main__":
    main()