"""Smoke tests to verify package imports."""


def test_import_package():
    """Test that the cricksy_scorer package can be imported."""
    import cricksy_scorer

    assert hasattr(cricksy_scorer, "__version__")


def test_import_modules():
    """Test that all main modules can be imported."""
    from cricksy_scorer import cli, config, io, main, models, scorer, utils

    # Verify modules are imported
    assert cli is not None
    assert config is not None
    assert io is not None
    assert main is not None
    assert models is not None
    assert scorer is not None
    assert utils is not None


def test_import_main_functions():
    """Test that main entry points can be imported."""
    from cricksy_scorer.main import run, main

    assert callable(run)
    assert callable(main)
