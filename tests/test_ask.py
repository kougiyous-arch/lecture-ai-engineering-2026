from types import SimpleNamespace

from app.ask import print_usage_metadata


def test_print_usage_metadata_reports_input_and_output_tokens(capsys):
    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=123,
            candidates_token_count=456,
            total_token_count=579,
        )
    )

    print_usage_metadata(response)

    captured = capsys.readouterr()
    assert "入力トークン数: 123" in captured.out
    assert "出力トークン数: 456" in captured.out
