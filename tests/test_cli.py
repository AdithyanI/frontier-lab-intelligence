import pytest

from fli import __version__
from fli.cli import main


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_args_prints_help(capsys):
    assert main([]) == 0
    assert "Frontier Lab Intelligence" in capsys.readouterr().out
