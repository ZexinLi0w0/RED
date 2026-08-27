from handler_signaling import _valid_handler_output


def test_handler_output_contract_rejects_caught_error_strings() -> None:
    assert _valid_handler_output(["Success"])
    assert not _valid_handler_output("Unexcepted Error: unsupported operation")
    assert not _valid_handler_output([])
