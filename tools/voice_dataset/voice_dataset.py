"""
Alat bantu dataset suara NandemoGHS/Japanese-Eroge-Voice-V2 (parquet lokal).

Perintah:
  list     -> ranking karakter berdasarkan total durasi audio (CSV)
  samples  -> ekspor beberapa klip contoh per karakter untuk didengarkan
  export   -> ekspor semua klip satu karakter + file .list format GPT-SoVITS (zip)

Contoh:
  python tools/voice_dataset/voice_dataset.py list
  python tools/voice_dataset/voice_dataset.py samples --top 20
  python tools/voice_dataset/voice_dataset.py export --rank 3 --name himari

Kebutuhan: pip install pyarrow
Catatan: karakter diidentifikasi dengan pasangan (source_dataset, char_id),
karena char_id adalah hash per game. Hanya baris text_source == "original"
(transkrip asli dari script game) yang dipakai; baris ASR tidak punya char_id.
"""

import argparse
import csv
import glob
import os
import random
import zipfile
from collections import defaultdict

import pyarrow.parquet as pq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA = os.path.join(ROOT, "data", "jp_dataset", "data")
DEFAULT_OUT = os.path.join(ROOT, "data", "voice_samples")

META_COLS = ["source_dataset", "char_id", "text", "text_source", "duration"]


def audio_ext(raw: bytes, path: str) -> str:
    """Tentukan ekstensi dari magic bytes (fallback ke ekstensi path asli)."""
    if raw[:4] == b"OggS":
        return "ogg"
    if raw[:4] == b"RIFF":
        return "wav"
    if raw[:4] == b"fLaC":
        return "flac"
    if raw[:3] == b"ID3" or (raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0):
        return "mp3"
    if raw[4:8] == b"ftyp":
        return "m4a"
    ext = os.path.splitext(path or "")[1].lstrip(".").lower()
    return ext or "bin"


def scan(data_dir):
    """Baca kolom metadata saja (tanpa audio). Return dict key -> list klip."""
    files = sorted(glob.glob(os.path.join(data_dir, "*.parquet")))
    if not files:
        raise SystemExit(f"Tidak ada file parquet di {data_dir}")
    chars = defaultdict(list)
    for fi, f in enumerate(files):
        pf = pq.ParquetFile(f)
        for rg in range(pf.num_row_groups):
            d = pf.read_row_group(rg, columns=META_COLS).to_pydict()
            for i in range(len(d["char_id"])):
                c = d["char_id"][i]
                if c and d["text_source"][i] == "original":
                    key = (d["source_dataset"][i], c)
                    chars[key].append({
                        "file": f, "rg": rg, "row": i,
                        "text": d["text"][i], "duration": d["duration"][i],
                    })
        print(f"\r[scan] {fi + 1}/{len(files)} shard", end="", flush=True)
    print()
    ranked = sorted(chars.items(), key=lambda kv: -sum(x["duration"] for x in kv[1]))
    return ranked


def fetch_audio(clips):
    """Ambil bytes audio hanya dari row group yang dibutuhkan."""
    by_rg = defaultdict(list)
    for c in clips:
        by_rg[(c["file"], c["rg"])].append(c)
    for n, ((f, rg), items) in enumerate(sorted(by_rg.items())):
        col = pq.ParquetFile(f).read_row_group(rg, columns=["audio"]).column("audio")
        for c in items:
            a = col[c["row"]].as_py()
            yield c, a["bytes"], a.get("path") or ""
        print(f"\r[audio] {n + 1}/{len(by_rg)} row group", end="", flush=True)
    print()


def char_label(rank, key):
    return f"{rank:03d}_{key[0][:6]}_{key[1][:6]}"


def cmd_list(args):
    ranked = scan(args.data)
    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, "characters.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "source_dataset", "char_id", "menit", "jumlah_klip", "contoh_teks"])
        for r, (key, clips) in enumerate(ranked, 1):
            total = sum(x["duration"] for x in clips)
            if total < args.min_minutes * 60:
                break
            w.writerow([r, key[0], key[1], round(total / 60, 1), len(clips), clips[0]["text"]])
    print(f"[list] {len(ranked)} karakter, ranking disimpan ke {out}")


def cmd_samples(args):
    ranked = scan(args.data)[: args.top]
    rnd = random.Random(42)
    wanted = []
    for r, (key, clips) in enumerate(ranked, 1):
        good = [c for c in clips if 3.0 <= c["duration"] <= 10.0] or clips
        for c in rnd.sample(good, min(args.per_char, len(good))):
            wanted.append(dict(c, label=char_label(r, key)))
    counters = defaultdict(int)
    for c, raw, path in fetch_audio(wanted):
        d = os.path.join(args.out, "samples", c["label"])
        os.makedirs(d, exist_ok=True)
        counters[c["label"]] += 1
        n = counters[c["label"]]
        with open(os.path.join(d, f"{n:02d}.{audio_ext(raw, path)}"), "wb") as fh:
            fh.write(raw)
        with open(os.path.join(d, "teks.txt"), "a", encoding="utf-8") as fh:
            fh.write(f"{n:02d}: {c['text']}\n")
    print(f"[samples] {len(ranked)} karakter diekspor ke {os.path.join(args.out, 'samples')}")


def cmd_export(args):
    ranked = scan(args.data)
    if not 1 <= args.rank <= len(ranked):
        raise SystemExit(f"rank harus 1..{len(ranked)}")
    key, clips = ranked[args.rank - 1]
    clips = [c for c in clips if args.min_sec <= c["duration"] <= args.max_sec]
    name = args.name or char_label(args.rank, key)
    os.makedirs(args.out, exist_ok=True)
    zpath = os.path.join(args.out, f"{name}.zip")
    lines, total, idx = [], 0.0, 0
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for c, raw, path in fetch_audio(clips):
            idx += 1
            stem = f"{idx:05d}"
            z.writestr(f"raw/{stem}.{audio_ext(raw, path)}", raw)
            # path di .list menunjuk ke wav hasil konversi di Colab
            text = c["text"].replace("|", " ").replace("\n", " ").strip().strip("「」『』").strip()
            lines.append(f"wavs/{stem}.wav|{name}|ja|{text}")
            total += c["duration"]
        z.writestr(f"{name}.list", "\n".join(lines) + "\n")
    print(f"[export] {idx} klip ({total / 60:.1f} menit) -> {zpath}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=DEFAULT_DATA, help="folder file parquet")
    p.add_argument("--out", default=DEFAULT_OUT, help="folder output")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list")
    s.add_argument("--min-minutes", type=float, default=5)
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("samples")
    s.add_argument("--top", type=int, default=20)
    s.add_argument("--per-char", type=int, default=3)
    s.set_defaults(fn=cmd_samples)

    s = sub.add_parser("export")
    s.add_argument("--rank", type=int, required=True, help="nomor rank dari characters.csv")
    s.add_argument("--name", help="nama speaker (huruf/angka saja)")
    s.add_argument("--min-sec", type=float, default=1.5)
    s.add_argument("--max-sec", type=float, default=15.0)
    s.set_defaults(fn=cmd_export)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
