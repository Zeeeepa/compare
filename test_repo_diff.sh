#!/bin/bash
echo "Creating test repositories..."

mkdir -p test_repo1
cd test_repo1
git init
echo "# Test Repository 1" > README.md
mkdir -p src
echo "function test() { return true; }" > src/main.js
mkdir -p docs
echo "# Documentation" > docs/index.md
git add .
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git commit -m "Initial commit for test repo 1"
echo "function newFeature() { return \"new\"; }" > src/feature.js
git add .
git commit -m "Add new feature"
git tag v1.0
cd ..

mkdir -p test_repo2
cd test_repo2
git init
echo "# Test Repository 2" > README.md
mkdir -p src
echo "function test() { return true; }" > src/main.js
mkdir -p config
echo '{ "setting": "value" }' > config/settings.json
git add .
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git commit -m "Initial commit for test repo 2"
git tag v1.0
cd ..

echo "Test repositories created successfully!"
echo ""
echo "Now you can use the Repository Comparison Tool to compare these test repositories."
echo ""
echo "Press Enter to start the tool..."
read
python3 repo_diff_gui_upgraded.py
