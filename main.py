"""Mini NPU Simulator

MAC(Multiply-Accumulate) 연산으로 입력 패턴이 어느 필터와 더 비슷한지 판별하는
콘솔 프로그램이다. 표준 라이브러리만 사용한다 (Python 3.8 이상).
"""

import time
import unicodedata

# 두 점수의 차이가 이 값보다 작으면 동점으로 본다 (부동소수점 오차 대비).
EPSILON = 1e-9
# 성능 분석에서 MAC 연산을 반복해 재는 횟수
REPEAT = 10

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
        print("data.json 분석은 아직 준비 중입니다.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print()
        print("입력이 끝나 프로그램을 종료합니다.")
