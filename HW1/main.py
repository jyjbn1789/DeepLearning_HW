name: Daily Yongin Weather Report (HW1)

on:
  schedule:
    # KST 08:00 = UTC 23:00 (전날)
    - cron: '0 23 * * *'
  workflow_dispatch: {}

jobs:
  run-weather-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Show Python / pip
        run: |
          python -V
          pip -V

      - name: Install dependencies
        # requirements.txt가 없다면: pip install requests 로 대체
        run: |
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          else
            pip install requests
          fi

      - name: Write kakao_tokens.json from secret (safe heredoc)
        # 레포 루트에 kakao_tokens.json 작성
        run: |
          cat > kakao_tokens.json << 'JSON_EOF'
          ${{ secrets.KAKAO_TOKENS_JSON }}
          JSON_EOF

      - name: Run script
        env:
          OPENWEATHERMAP_API_KEY: ${{ secrets.OWM_API_KEY }}
          KAKAO_REST_API_KEY:     ${{ secrets.KAKAO_REST_API_KEY }}
          CI: true   # CI 환경 표시 → 코드에서 최초 인증 프롬프트 방지
        run: |
          python main.py
