import argparse
import os
from pathlib import Path

import torch
from trainer import Trainer, TrainerArgs

from TTS.tts.configs.shared_configs import BaseAudioConfig, BaseDatasetConfig, CharactersConfig
from TTS.tts.configs.vits_config import VitsConfig
from TTS.tts.datasets import load_tts_samples
from TTS.tts.models.vits import Vits, VitsArgs
from TTS.tts.utils.speakers import SpeakerManager
from TTS.tts.utils.text.tokenizer import TTSTokenizer
from TTS.utils.audio import AudioProcessor
from TTS.utils.io import load_fsspec

VI_CHARACTERS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "àáảãạăằắẳẵặâầấẩẫậ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ"
    "đ"
    "Đ"
    "èéẻẽẹêềếểễệ"
    "ÈÉẺẼẸÊỀẾỂỄỆ"
    "ìíỉĩị"
    "ÌÍỈĨỊ"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ"
    "ùúủũụưừứửữự"
    "ÙÚỦŨỤƯỪỨỬỮỰ"
    "ỳýỷỹỵ"
    "ỲÝỶỸỴ"
)
VI_PUNCTUATIONS = "!'\"(),-.:;? []/…“”‘’–— "
PITCH_FMIN = 65.0
PITCH_FMAX = 640.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/fine-tune Vietnamese multi-speaker VITS with pitch contour loss.")
    parser.add_argument("--dataset-path", required=True, help="Dataset root containing wavs/ and metadata files.")
    parser.add_argument("--metadata-train", default="metadata_train.csv", help="Train metadata filename.")
    parser.add_argument("--metadata-val", default="metadata_val.csv", help="Validation metadata filename.")
    parser.add_argument("--run-name", default="vits_vi_multispeaker", help="Trainer run name.")
    parser.add_argument("--output-path", default=None, help="Output directory for checkpoints and logs.")
    parser.add_argument("--restore-path", default=None, help="Optional pretrained checkpoint path (.pth) for Transfer Learning (e.g. VCTK).")
    parser.add_argument("--restore-vietnamese-path", default=None, help="Optional explicit path to best_model.pth to resume training from previous run.")

    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=8)
    parser.add_argument("--batch-group-size", type=int, default=4)
    parser.add_argument("--num-loader-workers", type=int, default=2)
    parser.add_argument("--num-eval-loader-workers", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=600)
    parser.add_argument("--max-text-len", type=int, default=300)
    parser.add_argument("--max-audio-len", type=int, default=320000)
    parser.add_argument("--save-step", type=int, default=500, help="Save checkpoint every N steps.")
    parser.add_argument("--eval-step", type=int, default=1000, help="Run evaluation every N steps.")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping: stop if best_loss doesn't improve for N eval cycles. 0=disabled.")

    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate for both generator/discriminator.")
    parser.add_argument("--pitch-loss-alpha", type=float, default=0.1, help="Weight of custom pitch contour loss (applied on log-F0).")
    parser.add_argument("--text-cleaner", default="no_cleaners", help="Cleaner function in text.cleaners.")

    parser.add_argument("--use-phonemes", action="store_true", help="Enable phoneme frontend (experimental for vi).")
    parser.add_argument("--phoneme-language", default="vi", help="Phoneme language code when --use-phonemes is set.")
    parser.add_argument("--phonemizer", default=None, help="Optional phonemizer override (e.g., espeak).")

    parser.add_argument("--compute-f0", action="store_true", help="Enable cached F0 extraction for pitch supervision.")
    parser.add_argument("--f0-cache-path", default=None, help="Directory for F0 cache. Defaults to output_path/f0_cache.")
    parser.add_argument(
        "--lazy-f0",
        action="store_true",
        help="Skip full F0 precompute and compute/cache F0 on demand during training.",
    )
    parser.add_argument(
        "--full-f0-precompute",
        action="store_true",
        help="Disable lazy mode and force full F0 precompute before training.",
    )
    parser.add_argument(
        "--reuse-speaker-encoder-if-compatible",
        action="store_true",
        help="Load speaker_encoder tensors only when keys and tensor shapes match.",
    )
    parser.add_argument("--no-mixed-precision", action="store_true", help="Disable mixed precision training.")
    parser.add_argument(
        "--continue-path",
        default=None,
        help="Path to a previous run folder to resume training (optimizer + scheduler state kept)."
    )
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"Ignoring unknown args: {unknown}")
    return args


def load_pretrained_for_vietnamese(
    model: Vits, checkpoint_path: str, reuse_speaker_encoder_if_compatible: bool = False
) -> None:
    state = load_fsspec(checkpoint_path, map_location=torch.device("cpu"))
    model_state = state.get("model", state)

    current_state = model.state_dict()
    filtered = {}
    skipped = []
    loaded_speaker_related = 0
    for key, tensor in model_state.items():
        if key == "text_encoder.emb.weight":
            skipped.append(key)
            continue

        if key not in current_state:
            skipped.append(key)
            continue

        if current_state[key].shape != tensor.shape:
            skipped.append(key)
            continue

        if "speaker_encoder" in key and not reuse_speaker_encoder_if_compatible:
            skipped.append(key)
            continue

        filtered[key] = tensor
        if "speaker_encoder" in key or key.startswith("emb_g"):
            loaded_speaker_related += 1

    missing, unexpected = model.load_state_dict(filtered, strict=False)

    with torch.no_grad():
        nn_hidden = model.args.hidden_channels
        torch.nn.init.normal_(model.text_encoder.emb.weight, 0.0, nn_hidden ** -0.5)

    skipped_speaker_encoder = sum(1 for key in skipped if "speaker_encoder" in key)

    print(f"Loaded pretrained tensors: {len(filtered)}")
    print(f"Loaded speaker-related tensors: {loaded_speaker_related}")
    print(f"Skipped speaker_encoder tensors: {skipped_speaker_encoder}")
    print(f"Skipped tensors: {len(skipped)}")
    print(f"Missing keys after load: {len(missing)}")
    print(f"Unexpected keys after load: {len(unexpected)}")


if __name__ == "__main__":
    args = parse_args()

    enable_lazy_f0 = args.compute_f0 and (args.lazy_f0 or not args.full_f0_precompute)
    if enable_lazy_f0:
        os.environ["TTS_LAZY_F0"] = "1"
        print("Lazy F0 mode enabled via TTS_LAZY_F0=1")

    if args.pitch_loss_alpha > 0 and not args.compute_f0:
        print("Warning: pitch_loss_alpha > 0 but --compute-f0 is disabled, so pitch loss will be skipped.")

    recipe_root = Path(__file__).resolve().parent
    output_path = Path(args.output_path).resolve() if args.output_path else recipe_root / "outputs"
    output_path.mkdir(parents=True, exist_ok=True)

    dataset_path = Path(args.dataset_path).resolve()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    train_meta = dataset_path / args.metadata_train
    val_meta = dataset_path / args.metadata_val
    if not train_meta.exists():
        raise FileNotFoundError(f"Train metadata not found: {train_meta}")
    if not val_meta.exists():
        raise FileNotFoundError(f"Validation metadata not found: {val_meta}")

    f0_cache_path = Path(args.f0_cache_path).resolve() if args.f0_cache_path else output_path / "f0_cache"
    phoneme_cache_path = output_path / "phoneme_cache"

    dataset_config = BaseDatasetConfig(
        formatter="coqui",
        dataset_name="vi_three_region",
        path=str(dataset_path),
        meta_file_train=train_meta.name,
        meta_file_val=val_meta.name,
        language="vi",
    )

    audio_config = BaseAudioConfig(
        sample_rate=22050,
        win_length=1024,
        hop_length=256,
        num_mels=80,
        mel_fmin=0,
        mel_fmax=None,
        pitch_fmin=PITCH_FMIN,
        pitch_fmax=PITCH_FMAX,
    )

    model_args = VitsArgs(use_speaker_embedding=True)

    config = VitsConfig(
        model_args=model_args,
        audio=audio_config,
        run_name=args.run_name,
        batch_size=args.batch_size,
        eval_batch_size=args.eval_batch_size,
        batch_group_size=args.batch_group_size,
        num_loader_workers=args.num_loader_workers,
        num_eval_loader_workers=args.num_eval_loader_workers,
        run_eval=True,
        test_delay_epochs=-1,
        epochs=args.epochs,
        text_cleaner=args.text_cleaner,
        use_phonemes=args.use_phonemes,
        phoneme_language=args.phoneme_language if args.use_phonemes else None,
        phonemizer=args.phonemizer if args.use_phonemes else None,
        phoneme_cache_path=str(phoneme_cache_path) if args.use_phonemes else None,
        compute_input_seq_cache=True,
        print_step=25,
        print_eval=False,
        save_step=args.save_step,
        run_eval_steps=args.eval_step,
        save_best_after=0,
        mixed_precision=not args.no_mixed_precision,
        max_text_len=args.max_text_len,
        max_audio_len=args.max_audio_len,
        lr_gen=args.lr,
        lr_disc=args.lr,
        output_path=str(output_path),
        datasets=[dataset_config],
        compute_f0=args.compute_f0,
        f0_cache_path=str(f0_cache_path),
        pitch_loss_alpha=args.pitch_loss_alpha,
        use_weighted_sampler=True,
        weighted_sampler_attrs={"speaker_name": 1.0},
        weighted_sampler_multipliers={},
        characters=CharactersConfig(
            characters_class="TTS.tts.models.vits.VitsCharacters",
            pad="<PAD>",
            eos="<EOS>",
            bos="<BOS>",
            blank="<BLNK>",
            characters=VI_CHARACTERS,
            punctuations=VI_PUNCTUATIONS,
            phonemes=None,
        ),
        test_sentences=[
            ["Xin chào, đây là thử nghiệm giọng Bắc."],
            ["Trời hôm nay thật đẹp và trong xanh."],
            ["Giọng miền Nam nghe thật dễ chịu và ấm áp."],
        ],
    )

    # Force conversion of nested config objects before tokenizer init.
    config.from_dict(config.to_dict())

    ap = AudioProcessor.init_from_config(config)
    try:
        tokenizer, config = TTSTokenizer.init_from_config(config)
    except ValueError as error:
        if args.use_phonemes:
            raise RuntimeError(
                "Phoneme frontend initialization failed for Vietnamese. "
                "Try disabling --use-phonemes or install a compatible phonemizer backend."
            ) from error
        raise

    train_samples, eval_samples = load_tts_samples(
        config.datasets,
        eval_split=True,
        eval_split_max_size=config.eval_split_max_size,
        eval_split_size=config.eval_split_size,
    )

    speaker_manager = SpeakerManager()
    speaker_manager.set_ids_from_data(train_samples + eval_samples, parse_key="speaker_name")
    config.model_args.num_speakers = speaker_manager.num_speakers

    model = Vits(config, ap, tokenizer, speaker_manager=speaker_manager)

    if args.restore_path and not args.continue_path:
        restore_path = Path(args.restore_path).resolve()
        if not restore_path.exists():
            raise FileNotFoundError(f"Restore checkpoint not found: {restore_path}")
        print(f"Loading pretrained checkpoint (Transfer Learning): {restore_path}")
        load_pretrained_for_vietnamese(
            model,
            str(restore_path),
            reuse_speaker_encoder_if_compatible=args.reuse_speaker_encoder_if_compatible,
        )

    native_restore_path = ""
    if getattr(args, "restore_vietnamese_path", None) and not args.continue_path:
        native_restore_path = args.restore_vietnamese_path
        print(f"Loading native Vietnamese checkpoint (Resume): {native_restore_path}")

    trainer = Trainer(
        TrainerArgs(
            continue_path=args.continue_path or "",
            restore_path=native_restore_path,
        ),
        config,
        str(output_path),
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
    )

    # ---- Early stopping wrapper ----
    if args.patience > 0:
        _orig_eval = trainer.eval_epoch
        _best_loss = [float("inf")]
        _wait = [0]

        def _eval_with_early_stop():
            result = _orig_eval()
            avg = trainer.keep_avg_eval.avg_values if hasattr(trainer, 'keep_avg_eval') else {}
            print(f"  [debug] eval keys: {list(avg.keys())}")
            # VITS uses 'avg_loss_1' for total evaluation loss
            cur_loss = avg.get("avg_loss_1", avg.get("avg_loss_gen", float("inf")))
            if cur_loss < _best_loss[0]:
                _best_loss[0] = cur_loss
                _wait[0] = 0
                print(f"  [early-stop] eval loss improved to {cur_loss:.4f}, patience reset")
            else:
                _wait[0] += 1
                print(f"  [early-stop] no improvement ({cur_loss:.4f} >= {_best_loss[0]:.4f}), patience {_wait[0]}/{args.patience}")
            if _wait[0] >= args.patience:
                print(f"  [early-stop] patience exhausted after {_wait[0]} eval cycles. Stopping training.")
                raise KeyboardInterrupt("Early stopping triggered")
            return result

        trainer.eval_epoch = _eval_with_early_stop
        print(f"Early stopping enabled: patience={args.patience} eval cycles")

    trainer.fit()
