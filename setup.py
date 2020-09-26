from cx_Freeze import setup, Executable


includefiles = ["chromedriver.exe", "fichiers", "tracker"]
includes = []
excludes = ["tracker/classement.py", "tracker/precision.py"]
packages = ["pandas", "requests", "bs4", "urllib3", "selenium", "boltons", "tracker", "data", "tui", "web"]

setup(
    name='fourmizzz_auto_tracker',
    version='0',
    description="Traqueur auto pour fourmizzz",
    author='Chris ADAM',
    author_email='adam.chris@live.be',
    options={'build_exe': {'includes': includes,
                           'excludes': excludes,
                           'packages': packages,
                           'include_files': includefiles}},
    executables=[Executable('main.py')]
)
