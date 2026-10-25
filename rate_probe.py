"""Gemini API rate-limit experiment: bounded requests, no chat history or retries."""
import argparse
import csv
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from google import genai
from google.genai import errors, types

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()

parser = argparse.ArgumentParser(description="Gemini rate-limit probe")
parser.add_argument("--model", default="gemini-3.5-flash-lite")
parser.add_argument("--requests", type=int, default=15)
parser.add_argument("--workers", type=int, default=4)
parser.add_argument("--padding", type=int, default=0,
                    help="Number of repeated phrases added to the input (for TPM testing)")
parser.add_argument("--csv", default="rate_limit_results.csv")
args = parser.parse_args()
if not (1 <= args.requests <= 40 and 1 <= args.workers <= 5 and 0 <= args.padding <= 2000):
    parser.error("Use 1–40 requests, 1–5 workers, and 0–2000 padding phrases")

try:
    client = genai.Client(http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=1)
    ))
except Exception as exc:
    raise SystemExit(f"APIの初期化に失敗しました。app.askと同じAPIキー設定が必要です: {exc}")

prompt = "『了解』とだけ短く答えてください。" + (" 測定用テキスト。" * args.padding)
origin = time.perf_counter()
fields = ["model", "request", "start_s", "seconds", "status",
          "input_tokens", "output_tokens", "error"]


def run_one(n):
    start = time.perf_counter()
    row = {"model": args.model, "request": n,
           "start_s": round(start - origin, 3), "seconds": None,
           "status": "OK", "input_tokens": "", "output_tokens": "", "error": ""}
    try:
        response = client.models.generate_content(
            model=args.model, contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=64),
        )
        usage = response.usage_metadata
        if usage:
            row["input_tokens"] = usage.prompt_token_count or 0
            row["output_tokens"] = usage.candidates_token_count or 0
    except errors.APIError as exc:
        row["status"] = str(exc.code)
        row["error"] = str(exc).replace("\n", " ")[:400]
    except Exception as exc:
        row["status"] = "ERROR"
        row["error"] = f"{type(exc).__name__}: {exc}".replace("\n", " ")[:400]
    row["seconds"] = round(time.perf_counter() - start, 3)
    return row


results = []
stop = False
next_request = 1
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    futures = {}
    for _ in range(min(args.requests, args.workers)):
        futures[pool.submit(run_one, next_request)] = next_request
        next_request += 1
    while futures:
        done, _ = wait(futures, return_when=FIRST_COMPLETED)
        for future in done:
            futures.pop(future)
            row = future.result()
            results.append(row)
            print(f"#{row['request']:02d} {row['status']:>5} "
                  f"{row['seconds']:>7.3f}s input={row['input_tokens']} "
                  f"output={row['output_tokens']}", flush=True)
            if row["error"]:
                print("   ", row["error"][:220], flush=True)
            if row["status"] == "429":
                stop = True
        if not stop:
            for _ in done:
                if next_request <= args.requests:
                    futures[pool.submit(run_one, next_request)] = next_request
                    next_request += 1

results.sort(key=lambda row: row["request"])
output = Path(args.csv)
with output.open("a", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    if stream.tell() == 0:
        writer.writeheader()
    writer.writerows(results)

print(f"終了: {len(results)}件実行、成功={sum(r['status'] == 'OK' for r in results)}件、"
      f"429={sum(r['status'] == '429' for r in results)}件")
print(f"CSV保存先: {output.resolve()}")
