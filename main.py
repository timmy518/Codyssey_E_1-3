"""Mini NPU Simulator

MAC(Multiply-Accumulate) 연산으로 입력 패턴이 어느 필터와 더 비슷한지 판별하는
콘솔 프로그램이다. 표준 라이브러리만 사용한다 (Python 3.8 이상).
"""

import json
import os
import re
import time
import unicodedata

# 두 점수의 차이가 이 값보다 작으면 동점으로 본다 (부동소수점 오차 대비).
EPSILON = 1e-9
# 성능 분석에서 MAC 연산을 반복해 재는 횟수
REPEAT = 10
# data.json 모드의 성능 분석 크기
PERF_SIZES = (3, 5, 13, 25)

# data.json 은 main.py 와 같은 폴더에서 읽는다.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

# 프로그램 안에서 쓰는 표준 라벨
CROSS = "Cross"
X = "X"
UNDECIDED = "UNDECIDED"
# data.json 의 여러 표기를 표준 라벨로 바꾸는 표 (앞뒤 공백을 지우고 소문자로 맞춘 뒤 찾는다)
LABEL_MAP = {"+": CROSS, "cross": CROSS, "x": X}

FILTER_KEY = re.compile(r"size_(\d+)")
PATTERN_KEY = re.compile(r"size_(\d+)_(\d+)")

DIVIDER = "#" + "-" * 39


# ---------------------------------------------------------------
# 데이터 구조: n×n 2차원 배열 (리스트 안에 행 리스트를 담는다)
# ---------------------------------------------------------------

def create_matrix(size, fill=0.0):
    """size×size 2차원 배열을 만든다. 모든 칸을 fill 값으로 채운다."""
    return [[fill] * size for _ in range(size)]


def get_value(matrix, row, col):
    """(row, col) 위치의 값을 읽는다."""
    return matrix[row][col]


def set_value(matrix, row, col, value):
    """(row, col) 위치에 값을 저장한다."""
    matrix[row][col] = value


def shape_of(matrix):
    """숫자로 된 2차원 배열이면 (행 수, 열 수) 를, 아니면 None 을 돌려준다.

    행마다 열 수가 다르거나 숫자가 아닌 값이 섞여 있어도 None 이다.
    """
    if not isinstance(matrix, list):
        return None
    cols = None
    for row in matrix:
        if not isinstance(row, list):
            return None
        if cols is None:
            cols = len(row)
        elif len(row) != cols:
            return None
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
    return len(matrix), cols or 0


# ---------------------------------------------------------------
# 라벨 정규화: 여러 표기를 표준 라벨(Cross, X) 하나로 맞춘다
# ---------------------------------------------------------------

def normalize_label(raw):
    """'+', 'cross', 'x' 같은 표기를 표준 라벨로 바꾼다. 모르는 표기면 None 을 돌려준다."""
    if not isinstance(raw, str):
        return None
    return LABEL_MAP.get(raw.strip().lower())


# ---------------------------------------------------------------
# 패턴 생성: N×N 십자가(Cross)와 X 패턴을 만든다
# ---------------------------------------------------------------

def generate_cross(size):
    """가운데 행과 가운데 열이 1 인 size×size 십자가 패턴을 만든다."""
    matrix = create_matrix(size)
    center = size // 2
    for i in range(size):
        set_value(matrix, center, i, 1.0)
        set_value(matrix, i, center, 1.0)
    return matrix


def generate_x(size):
    """두 대각선이 1 인 size×size X 패턴을 만든다."""
    matrix = create_matrix(size)
    for i in range(size):
        set_value(matrix, i, i, 1.0)
        set_value(matrix, i, size - 1 - i, 1.0)
    return matrix


# ---------------------------------------------------------------
# MAC 연산: 외부 라이브러리 없이 반복문으로 직접 구현
# ---------------------------------------------------------------

def mac(pattern, filt):
    """같은 위치의 값끼리 곱하고(Multiply) 모두 더한(Accumulate) 점수를 돌려준다."""
    size = len(pattern)
    total = 0.0
    for row in range(size):
        for col in range(size):
            total += pattern[row][col] * filt[row][col]
    return total


# ---------------------------------------------------------------
# 점수 비교 정책: 허용오차(epsilon) 기반, 동점이면 판정하지 않는다
# ---------------------------------------------------------------

def judge(score_a, score_b, label_a, label_b, tie_label):
    """두 점수를 EPSILON 기준으로 비교해 판정 라벨을 돌려준다.

    차이가 EPSILON 보다 작으면 동점(tie_label), 아니면 점수가 큰 쪽의 라벨이다.
    """
    if abs(score_a - score_b) < EPSILON:
        return tie_label
    if score_a > score_b:
        return label_a
    return label_b


# ---------------------------------------------------------------
# 성능 측정
# ---------------------------------------------------------------

def measure_ms(func, pattern, filt, repeat=REPEAT):
    """func(pattern, filt) 를 repeat 번 호출해 1회 평균 시간(ms)을 돌려준다.

    입력, 출력, 파일 읽기 시간은 빼고 연산 함수를 호출하는 구간만 잰다.
    """
    total = 0.0
    for _ in range(repeat):
        start = time.perf_counter()
        func(pattern, filt)
        total += time.perf_counter() - start
    return total / repeat * 1000


# ---------------------------------------------------------------
# 출력 도우미
# ---------------------------------------------------------------

def print_section(title):
    """구역 제목을 구분선과 함께 출력한다."""
    print()
    print(DIVIDER)
    print(f"# {title}")
    print(DIVIDER)


def display_width(text):
    """콘솔 화면 너비를 센다. 한글처럼 두 칸을 차지하는 글자는 2 로 센다."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def fit(text, width, right=False):
    """text 를 화면 너비 width 에 맞게 공백으로 채운다. right 가 참이면 오른쪽 정렬."""
    space = " " * max(0, width - display_width(text))
    return space + text if right else text + space


def print_performance_table(rows):
    """크기별 성능 표를 출력한다. rows 는 (N, 평균 시간 ms) 목록이다."""
    header = fit("크기(N×N)", 10) + fit("평균 시간(ms)", 16, True) + fit("연산 횟수(N²)", 16, True)
    print(header)
    print("-" * display_width(header))
    for size, ms in rows:
        print(fit(f"{size}×{size}", 10) + fit(f"{ms:.4f}", 16, True) + fit(str(size * size), 16, True))


# ---------------------------------------------------------------
# 모드 1: 사용자 입력 (3×3)
# ---------------------------------------------------------------

def parse_row(line, size):
    """공백으로 구분된 숫자 size 개를 읽는다.

    성공하면 (숫자 목록, None), 형식이 틀리면 (None, 안내 문구) 를 돌려준다.
    """
    parts = line.split()
    if len(parts) != size:
        return None, f"입력 형식 오류: 각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요."
    try:
        return [float(part) for part in parts], None
    except ValueError:
        return None, (f"입력 형식 오류: 숫자가 아닌 값이 있습니다. "
                      f"각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요.")


def read_matrix(title, size=3):
    """size 줄을 한 줄씩 입력받아 size×size 배열에 저장한다.

    열 수가 다르거나 숫자가 아닌 값이 있는 줄은 안내 문구를 보여 주고 그 줄을 다시 받는다.
    """
    print(f"{title} ({size}줄 입력, 공백 구분)")
    matrix = create_matrix(size)
    row = 0
    while row < size:
        values, error = parse_row(input(), size)
        if error:
            print(error)
            print(f"{row + 1}번째 줄을 다시 입력하세요.")
            continue
        for col, value in enumerate(values):
            set_value(matrix, row, col, value)
        row += 1
    return matrix


def run_user_mode():
    """모드 1: 3×3 필터 A, B 와 패턴을 입력받아 MAC 점수로 판정한다."""
    print_section("[1] 필터 입력")
    filter_a = read_matrix("필터 A")
    filter_b = read_matrix("필터 B")
    print("필터 A, B 저장 완료")

    print_section("[2] 패턴 입력")
    pattern = read_matrix("패턴")

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    decision = judge(score_a, score_b, "A", "B", "판정 불가")
    # MAC 1회(패턴 × 필터 하나) 평균 시간. 필터 A, B 를 각각 REPEAT 번 재서 평균한다.
    elapsed = (measure_ms(mac, pattern, filter_a) + measure_ms(mac, pattern, filter_b)) / 2

    print_section("[3] MAC 결과")
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/{REPEAT}회): {elapsed:.4f} ms")
    if decision == "판정 불가":
        print(f"판정: 판정 불가 (|A-B| < {EPSILON:g})")
    else:
        print(f"판정: {decision}")

    print_section(f"[4] 성능 분석 (평균/{REPEAT}회)")
    print_performance_table([(3, elapsed)])


# ---------------------------------------------------------------
# 모드 2: data.json 분석
# ---------------------------------------------------------------

def load_json(path):
    """JSON 파일을 읽는다. 성공하면 (데이터, None), 실패하면 (None, 오류 문구)."""
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file), None
    except FileNotFoundError:
        return None, f"data.json 파일을 찾을 수 없습니다: {path}"
    except (OSError, ValueError) as error:
        return None, f"data.json 을 읽을 수 없습니다: {error}"


def load_filters(data):
    """data["filters"] 를 읽어 크기별 필터를 표준 라벨로 정리한다.

    돌려주는 값: (filters, problems)
    - filters: {"size_5": {"Cross": 배열, "X": 배열}, ...} 처럼 쓸 수 있는 필터
    - problems: {"size_13": "원인", ...} 처럼 쓸 수 없는 필터와 그 원인
    """
    filters = {}
    problems = {}
    raw_filters = data.get("filters")
    if not isinstance(raw_filters, dict):
        return filters, {"filters": "filters 항목이 없거나 형식이 다릅니다"}

    for key, group in raw_filters.items():
        match = FILTER_KEY.fullmatch(key)
        if not match:
            problems[key] = "키 형식 오류 (size_{N} 형태가 아닙니다)"
            continue
        if not isinstance(group, dict):
            problems[key] = "필터 묶음이 객체가 아닙니다"
            continue
        size = int(match.group(1))
        loaded = {}
        for label_key, matrix in group.items():
            label = normalize_label(label_key)
            if label is None:
                problems[key] = f"알 수 없는 필터 키 '{label_key}'"
                break
            shape = shape_of(matrix)
            if shape != (size, size):
                found = "숫자 2차원 배열 아님" if shape is None else f"{shape[0]}×{shape[1]}"
                problems[key] = f"{label} 필터 크기 불일치 ({found}, 필요 {size}×{size})"
                break
            loaded[label] = matrix
        else:
            missing = [label for label in (CROSS, X) if label not in loaded]
            if missing:
                problems[key] = f"{', '.join(missing)} 필터가 없습니다"
            else:
                filters[key] = loaded
    return filters, problems


def evaluate_case(key, case, filters, problems):
    """패턴 하나를 검증하고 판정한다. 결과를 딕셔너리로 돌려준다.

    키 해석, 필터 선택, 스키마, 크기 검사 중 하나라도 실패하면 프로그램을 멈추지 않고
    그 케이스만 FAIL 로 처리해 reason 에 원인을 남긴다.
    """
    result = {"key": key, "cross": None, "x": None, "decision": None,
              "expected": None, "passed": False, "reason": None}

    # 1) 키 size_{N}_{idx} 에서 N 을 꺼내 size_N 필터를 고른다.
    match = PATTERN_KEY.fullmatch(key)
    if not match:
        result["reason"] = "키 형식 오류 (size_{N}_{idx} 형태가 아닙니다)"
        return result
    size = int(match.group(1))
    filter_key = f"size_{size}"
    if filter_key not in filters:
        if filter_key in problems:
            result["reason"] = f"{filter_key} 필터를 쓸 수 없습니다: {problems[filter_key]}"
        else:
            result["reason"] = f"{filter_key} 필터가 없습니다"
        return result

    # 2) 스키마: input 과 expected 가 있어야 하고, expected 는 표준 라벨로 바꾼다.
    if not isinstance(case, dict) or "input" not in case or "expected" not in case:
        result["reason"] = "스키마 오류 (input 또는 expected 항목이 없습니다)"
        return result
    expected = normalize_label(case["expected"])
    if expected is None:
        result["reason"] = f"expected 라벨을 해석할 수 없습니다 ({case['expected']!r})"
        return result
    result["expected"] = expected

    # 3) 패턴과 필터의 크기가 같은지 확인한다.
    shape = shape_of(case["input"])
    if shape is None:
        result["reason"] = "패턴이 숫자로 된 2차원 배열이 아닙니다"
        return result
    if shape != (size, size):
        result["reason"] = f"크기 불일치 (패턴 {shape[0]}×{shape[1]}, 필터 {size}×{size})"
        return result

    # 4) MAC 점수를 구해 판정하고 expected 와 비교한다.
    pattern = case["input"]
    cross_score = mac(pattern, filters[filter_key][CROSS])
    x_score = mac(pattern, filters[filter_key][X])
    decision = judge(cross_score, x_score, CROSS, X, UNDECIDED)
    result.update(cross=cross_score, x=x_score, decision=decision)
    if decision == UNDECIDED:
        result["reason"] = "동점(UNDECIDED) 처리 규칙"
    elif decision != expected:
        result["reason"] = f"판정({decision})과 expected({expected}) 불일치"
    else:
        result["passed"] = True
    return result


def print_case(result):
    """케이스 하나의 점수, 판정, PASS/FAIL 을 출력한다."""
    print(f"--- {result['key']} ---")
    if result["decision"] is None:
        # 점수를 계산하기 전에 검증에서 걸린 케이스
        print(f"FAIL: {result['reason']}")
        return
    print(f"{CROSS} 점수: {result['cross']}")
    print(f"{X} 점수: {result['x']}")
    status = "PASS" if result["passed"] else f"FAIL ({result['reason']})"
    print(f"판정: {result['decision']} | expected: {result['expected']} | {status}")


def print_summary(results):
    """전체 테스트 수, 통과 수, 실패 수와 실패 케이스 목록을 출력한다."""
    failed = [result for result in results if not result["passed"]]
    print(f"총 테스트: {len(results)}개")
    print(f"통과: {len(results) - len(failed)}개")
    print(f"실패: {len(failed)}개")
    print()
    if failed:
        print("실패 케이스:")
        for result in failed:
            print(f"- {result['key']}: {result['reason']}")
    else:
        print("실패 케이스: 없음")


def run_json_mode(path=DATA_FILE):
    """모드 2: data.json 의 필터와 패턴을 읽어 한꺼번에 판정한다."""
    print_section("[1] 필터 로드")
    data, error = load_json(path)
    if error:
        print(error)
        return
    if not isinstance(data, dict):
        print("스키마 오류: data.json 의 최상위가 객체가 아닙니다.")
        return

    filters, problems = load_filters(data)
    raw_filters = data.get("filters")
    # data.json 에 적힌 순서대로 결과를 보여 준다.
    for key in raw_filters if isinstance(raw_filters, dict) else problems:
        if key in filters:
            print(f"{key} 필터 로드 완료 ({CROSS}, {X})")
        else:
            print(f"{key} 필터 로드 실패: {problems[key]}")

    print_section("[2] 패턴 분석 (라벨 정규화 적용)")
    patterns = data.get("patterns")
    if not isinstance(patterns, dict):
        print("스키마 오류: patterns 항목이 없거나 형식이 다릅니다.")
        patterns = {}
    results = []
    for key, case in patterns.items():
        result = evaluate_case(key, case, filters, problems)
        print_case(result)
        results.append(result)

    # 연산 시간은 크기에만 달려 있으므로, 크기마다 같은 방식으로 만든 십자가 패턴과
    # X 필터로 잰다. data.json 에 없는 3×3 도 같은 방식으로 포함한다.
    print_section(f"[3] 성능 분석 (평균/{REPEAT}회)")
    rows = []
    for size in PERF_SIZES:
        rows.append((size, measure_ms(mac, generate_cross(size), generate_x(size))))
    print_performance_table(rows)

    print_section("[4] 결과 요약")
    print_summary(results)


# ---------------------------------------------------------------
# 시작: 모드 선택
# ---------------------------------------------------------------

def main():
    print("=== Mini NPU Simulator ===")
    print()
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    choice = input("선택: ").strip()
    while choice not in ("1", "2"):
        print("1 또는 2를 입력하세요.")
        choice = input("선택: ").strip()

    if choice == "1":
        run_user_mode()
    else:
        run_json_mode()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print()
        print("입력이 끝나 프로그램을 종료합니다.")
