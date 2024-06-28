echo "--- Flake 8 ---"
flake8 .
echo "--- Black ---"
black . --check
echo "--- Isort ---"
isort . --check-only --profile black
echo "--- Bandit ---"
bandit .
echo "--- Sefety ---"
safety check
