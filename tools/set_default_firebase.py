"""index.html 이 처음 열리는 순간부터 정해 둔 Firebase 방에 저장되도록 연결 코드를 넣는다.

사용법:
  python3 tools/set_default_firebase.py WED1.xxxxx     # 연결 코드를 기본으로 설정
  python3 tools/set_default_firebase.py --clear        # 연결 코드를 제거 (각자 초대 링크로 연결). Firebase 설정값(config)은 그대로 둔다

연결 코드는 대시보드의 연결 설정 창에서 "연결 코드로 보내기"로 복사할 수 있다.

주의: 연결 코드가 index.html 안에 들어가므로, 이 페이지의 소스를 볼 수 있는 사람은 누구나 데이터를 읽고 고칠 수 있다.
공개 레포나 공개 주소로 올리지 말고, 두 분만 접근할 수 있는 곳에서만 쓴다.
"""
import base64
import json
import re
import sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "index.html"
PAT = re.compile(r'(<script id="firebase-default" type="application/json">)(.*?)(</script>)', re.S)


def valid(code):
    try:
        o = json.loads(base64.b64decode(code.strip().removeprefix("WED1.")))
        return bool(o["c"]["projectId"]) and re.fullmatch(r"[A-Z2-7]{16,40}", o["r"]) is not None
    except Exception:
        return False


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    html = HTML.read_text(encoding="utf-8")
    m = PAT.search(html)
    if not m:
        sys.exit("index.html 에 firebase-default 스크립트 태그가 없습니다.")
    cur = json.loads(m.group(2) or "{}")          # config 는 그대로 두고 code 만 바꾼다
    if arg == "--clear":
        cur.pop("code", None)
    elif valid(arg):
        cur["code"] = arg.strip()
    else:
        sys.exit("연결 코드가 올바르지 않습니다. WED1. 로 시작하는 코드를 통째로 넣어 주세요.")
    data = json.dumps(cur, ensure_ascii=False)
    HTML.write_text(PAT.sub(lambda m: m.group(1) + data + m.group(3), html, count=1), encoding="utf-8")
    print("기본 연결을 제거했습니다." if arg == "--clear" else "기본 연결을 설정했습니다. 공개 주소로 올리지 마세요.")


if __name__ == "__main__":
    main()
