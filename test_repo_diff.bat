@echo off
echo Creating test repositories...

mkdir test_repo1
cd test_repo1
git init
echo # Test Repository 1 > README.md
mkdir src
echo function test() { return true; } > src/main.js
mkdir docs
echo # Documentation > docs/index.md
git add .
git commit -m "Initial commit for test repo 1"
echo function newFeature() { return "new"; } > src/feature.js
git add .
git commit -m "Add new feature"
git tag v1.0
cd ..

mkdir test_repo2
cd test_repo2
git init
echo # Test Repository 2 > README.md
mkdir src
echo function test() { return true; } > src/main.js
mkdir config
echo { "setting": "value" } > config/settings.json
git add .
git commit -m "Initial commit for test repo 2"
git tag v1.0
cd ..

echo Test repositories created successfully!
echo.
echo Now you can use the Repository Comparison Tool to compare these test repositories.
echo.
echo Press any key to start the tool...
pause > nul
python repo_diff_gui.py
