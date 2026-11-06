# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：
素のLLMでは文章を入力すると、次の文章を生成することを行うが、エージェントではLLMにツールを見せて、必要に応じて呼び出すループをつけたものである。
- `--trace` で見えたツール呼び出し（ツール名と引数）：
[tool call]   make_quiz({'lecture': 2})
[tool return] make_quiz -> 第2回の確認問題: 「ランク（LoRAのr）」とは何ですか？
答え: LoRAで使う低ランク行列の大きさを決めるハイパーパラメータ。大きいほど表現力が上がるが、学習するパラメータとメモリも増える。
- 1つの質問での LLM 呼び出し回数（`requests`）：
requests=2
- 追加したツールと、docstring に書いた説明：
def make_quiz(lecture: int) -> str:
    """指定した回の用語から1つを選び、確認問題と答えを返す。

    「第2回の確認問題を出して」のように、復習用に問題を求められたときに使う。
    lecture には1始まりの回番号を入れる。
    """
    glossary = load_glossary()
    candidates = [entry for entry in glossary if entry["lecture"] == lecture]
    if not candidates:
        available = sorted({entry["lecture"] for entry in glossary})
        return (
            f"第{lecture}回の確認問題はまだありません。"
            f"用意されている回: {', '.join(f'第{n}回' for n in available)}"
        )

    term = random.choice(candidates)
    return (
        f"第{lecture}回の確認問題: 「{term['term']}」とは何ですか？\n"
        f"答え: {term['definition']}"
    )
## 宿題

- 取り組んだレベル：基礎 / 実装 / 発展
- やったこと：
- 結果：
- 気づき・疑問：
