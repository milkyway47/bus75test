# 使い方:
#   1) pip install edge-tts mutagen
#   2) python make_audio.py --sample          ... 声のサンプル(女性/男性)を作る
#   3) python make_audio.py --voice ja-JP-NanamiNeural   ... 全音声を作る（先頭に1秒の無音付き）
#   リポジトリ直下から作り直す場合: python tools/make_audio.py --json tools/narration.json --out audio
# Windowsで python が通らない場合は py に置き換えてください。
import argparse, asyncio, json, os, sys

try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts が入っていません。先に  pip install edge-tts mutagen  を実行してください。")
try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None

VOICES = {"nanami": "ja-JP-NanamiNeural", "keita": "ja-JP-KeitaNeural"}
SAMPLE = "左手に、江戸城の外堀が広がります。水面の釣り堀は、中央線の車窓でもおなじみの風景です。立売堀と書いて、いたちぼりと読みます。"

async def synth(text, voice, path, rate, pad=0.0):
    await edge_tts.Communicate(text, voice, rate=rate).save(path)
    if pad > 0:
        add_silence(path, pad)

# 先頭に無音を足す（再生開始直後に頭が切れる端末向け）。
# 元の音声と同じ形式の「中身が空のMP3フレーム」を並べて、ファイルの前につなげる。
def add_silence(path, sec):
    data = open(path, "rb").read()
    h = data[:4]
    if h[0] != 0xFF or (h[1] & 0xE6) != 0xE2:
        sys.exit(f"{path}: MP3フレームで始まっていないため無音を追加できません")
    mpeg1 = (h[1] >> 3) & 1
    br = ([0,32,40,48,56,64,80,96,112,128,160,192,224,256,320] if mpeg1 else
          [0,8,16,24,32,40,48,56,64,80,96,112,128,144,160])[h[2] >> 4] * 1000
    sr = [[22050,24000,16000],[44100,48000,32000]][mpeg1][(h[2] >> 2) & 3]
    if (h[1] >> 3) & 3 == 0: sr //= 2  # MPEG2.5
    size = (144 if mpeg1 else 72) * br // sr
    spf = 1152 if mpeg1 else 576
    frame = bytes([h[0], h[1], h[2] & 0xFD, h[3]]) + bytes(size - 4)
    open(path, "wb").write(frame * round(sec * sr / spf) + data)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="声のサンプルだけ作る")
    ap.add_argument("--voice", default=VOICES["nanami"], help="例: ja-JP-NanamiNeural / ja-JP-KeitaNeural")
    ap.add_argument("--rate", default="+0%", help="速度 例: -10%% / +10%%")
    ap.add_argument("--json", default="narration.json")
    ap.add_argument("--out", default="audio")
    ap.add_argument("--pad", type=float, default=1.0, help="先頭に入れる無音の秒数")
    a = ap.parse_args()

    if a.sample:
        for k, v in VOICES.items():
            fn = f"sample_{k}.mp3"
            await synth(SAMPLE, v, fn, a.rate, a.pad)
            print("作成:", fn)
        print("sample_nanami.mp3 / sample_keita.mp3 を再生して聴き比べてください。")
        return

    data = json.load(open(a.json, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    manifest = {"voice": a.voice, "rate": a.rate, "pad": a.pad, "segments": []}
    total = sum(len(s["parts"]) for s in data["segments"]); n = 0
    for seg in data["segments"]:
        entry = {"index": seg["index"], "stop": seg["stop"], "minutes": seg["minutes"], "parts": []}
        for p in seg["parts"]:
            n += 1
            fn = f'{p["id"]}.mp3'
            path = os.path.join(a.out, fn)
            await synth(p["text"], a.voice, path, a.rate, a.pad)
            dur = round(MP3(path).info.length, 2) if MP3 else round(len(p["text"]) / 6, 2)
            entry["parts"].append({"id": p["id"], "k": p["k"], "type": p.get("type", "L"), "file": fn, "sec": dur})
            print(f"[{n}/{total}] {fn} {dur}s")
        manifest["segments"].append(entry)
        # 区間の所要時間に対する余裕をチェック
        need = sum(x["sec"] for x in entry["parts"])
        lim = seg["minutes"] * 60 - 12
        if need > lim:
            print(f'  ※ {seg["stop"]}: 合計{need:.0f}秒 > 上限{lim}秒（アプリ側で豆知識から省略します）')
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("完了。audio フォルダの中身をすべてGitHubにアップロードしてください。")

asyncio.run(main())
