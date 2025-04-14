from setuptools import setup, find_packages

setup(
    name="repo-comparison-tool",
    version="1.1.0",
    description="A GUI tool for comparing two Git repositories",
    author="Zeeeepa",
    packages=find_packages(),
    install_requires=[
        "ttkthemes",
        "pillow",
        "gitpython",
    ],
    entry_points={
        "console_scripts": [
            "repo-diff=repo_diff_gui_upgraded:main",
        ],
    },
    python_requires=">=3.6",
)
