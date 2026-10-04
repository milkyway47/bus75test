# 使い方:
#   1) pip install edge-tts mutagen
#   2) python make_audio.py --sample          ... 声のサンプル(女性/男性)を作る
#   3) python make_audio.py --voice ja-JP-NanamiNeural   ... 全音声を作る
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

async def synth(text, voice, path, rate):
    await edge_tts.Communicate(text, voice, rate=rate).save(path)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="声のサンプルだけ作る")
    ap.add_argument("--voice", default=VOICES["nanami"], help="例: ja-JP-NanamiNeural / ja-JP-KeitaNeural")
    ap.add_argument("--rate", default="+0%", help="速度 例: -10%% / +10%%")
    ap.add_argument("--json", default="narration.json")
    ap.add_argument("--out", default="audio")
    a = ap.parse_args()

    if a.sample:
        for k, v in VOICES.items():
            fn = f"sample_{k}.mp3"
            await synth(SAMPLE, v, fn, a.rate)
            print("作成:", fn)
        print("sample_nanami.mp3 / sample_keita.mp3 を再生して聴き比べてください。")
        return

    data = json.load(open(a.json, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    manifest = {"voice": a.voice, "rate": a.rate, "segments": []}
    total = sum(len(s["parts"]) for s in data["segments"]); n = 0
    for seg in data["segments"]:
        entry = {"index": seg["index"], "stop": seg["stop"], "minutes": seg["minutes"], "parts": []}
        for p in seg["parts"]:
            n += 1
            fn = f'{p["id"]}.mp3'
            path = os.path.join(a.out, fn)
            await synth(p["text"], a.voice, path, a.rate)
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
