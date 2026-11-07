"""Mini NPU Simulator

MAC(Multiply-Accumulate) 연산으로 입력 패턴이 어느 필터와 더 비슷한지 판별하는
콘솔 프로그램이다. 표준 라이브러리만 사용한다 (Python 3.8 이상).
"""

# 두 점수의 차이가 이 값보다 작으면 동점으로 본다 (부동소수점 오차 대비).
EPSILON = 1e-9


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
