import pytest
import utils


class TestPLAnsatz:
    def test_parse(self, monkeypatch):
        local_list = []
        monkeypatch.setattr(utils, "save_json", lambda result, file_name: local_list.append(result))
        utils.sum_func(1, a=2, b=3, c=4)
        assert local_list[0]["res"] == '10'
