import os
import sys
import click
from app import create_app, db
from app.models import User, Role, Permission, Follow, Post, Comment
from flask_migrate import Migrate


COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage
    COV = coverage.coverage(branch=True, include="app/*")
    COV.start()

evn = os.environ.get("FLASK_CONFIG", "default")
app = create_app(evn)
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission, Follow=Follow, Post=Post,
                Comment=Comment)


@app.cli.command()
@click.option("--coverage/--no-coverage", default=False, help="Run tests under code coverage")
def test(coverage):
    """Run the unit tests."""
    if coverage and not os.environ.get("FLASK_COVERAGE"):
        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable]+[sys.argv[0]+".exe"]+sys.argv[1:])
    import unittest
    tests = unittest.TestLoader().discover("tests")
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print("Coverage Summary:")
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, "tmp/coverage")
        COV.html_report(directory=covdir)
        print("HTML version: file://%s/index.html" % covdir)
        COV.erase()

