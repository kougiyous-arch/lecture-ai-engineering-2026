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

- 取り組んだレベル：基礎
- やったこと：Instructionsに明確に問題と答えを出力するように記述した。また、docstringにクイズとは関係ないことを書いた。
- 結果：Instructionsを変更する前は、ヒントのみで答えは出力されていなかったが、変更後は答えが出力された。docstringを変えた場合は、make_quizが呼び出されずに、get_lecture_summaryから問題が作成されていた。
- 気づき・疑問：Instructionsによって、AIの挙動が明確に変化することを理解した。関数に明確な使用方法を記述しておかないと、AIが意図をくみ取れないことが分かった。

- 取り組んだレベル：実装
- やったこと：学習データの保存を行うための関数の作成、ツールとしての登録。
- 結果：learning_logフォルダ内にlearning_log.mdを作成し、保存時刻、学習内容、第何回の学習なのかを保存した。
- 気づき・疑問：記録を追記するだけでなく、第何回かを基準に並べ替えるツールも作れると考えた

- 取り組んだレベル：発展
- やったこと：Pydantic AIで作成した学習支援エージェントをGoogle ADKで作り直し、指示文とツールの渡し方、および同じ質問に対する回答を比較した。
- 結果：Pydantic AIでは`Agent(instructions=...)`で指示を設定し、`tool_plain()`でツールを個別に登録する。一方、Google ADKでは`Agent()`の`instruction`と`tools`に指示文とツールをまとめて渡す。同じ「第2回の内容から確認問題を1問出して」という質問に対して、出題された用語は異なるものの、どちらも適切な問題と解答を生成しており、回答内容や品質に大きな違いは見られなかった。
- 気づき・疑問：同じ指示文とツールを使用すれば、異なるフレームワークでも同様の機能を実現できることが分かった。また、Google ADKでは対話型CLIが標準で用意されており、会話の継続が容易である点が便利だと感じた。