from evaluation.run_evaluation import run

def test_runner_creates_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from pathlib import Path
    import shutil
    # Copy evaluation fixture and handbook because runner uses documented project-relative paths.
    src=Path(__file__).parents[1]
    shutil.copytree(src/'evaluation',tmp_path/'evaluation')
    shutil.copytree(src/'rag',tmp_path/'rag')
    rows=run('reports/result.csv')
    assert len(rows)==20 and (tmp_path/'reports/result.csv').exists()
